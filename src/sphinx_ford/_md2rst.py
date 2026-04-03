"""Markdown to RST converter for FORD doc comments.

Uses *markdown-it-py* for CommonMark-compliant parsing with a custom RST
renderer.  FORD-specific syntax (``[[xref]]``, ``@note``/``@endnote``)
is handled via pre/post-processing around the Markdown parser.
"""

from __future__ import annotations

import re
from typing import Any

from markdown_it import MarkdownIt

# FORD admonition types to RST directive names
_FORD_ADMONITIONS = {
    "note": "note",
    "warning": "warning",
    # Use note so generated docs do not require sphinx.ext.todo.
    "todo": "note",
    "bug": "danger",
    "history": "versionchanged",
}

_ADM_KEYS = "|".join(_FORD_ADMONITIONS)
_RE_ADM_END = re.compile(r"@end(" + _ADM_KEYS + r")\s*$", re.IGNORECASE)
_RE_ADM_START = re.compile(r"@(" + _ADM_KEYS + r")\b\s*(.*)", re.IGNORECASE)

# Unicode noncharacters used as placeholders: they survive markdown-it
# parsing and are never present in real FORD doc comments.
_XREF_S = "\ufdd0"  # start sentinel
_XREF_E = "\ufdd1"  # end sentinel

_HEADING_CHARS = "=-~^\"'"


def _preprocess_xrefs(text: str) -> tuple[str, list[str]]:
    """Replace ``[[entity]]`` with placeholders before parsing."""
    xrefs: list[str] = []

    def _sub(m: re.Match) -> str:
        xrefs.append(m.group(1))
        return f"{_XREF_S}{len(xrefs) - 1}{_XREF_E}"

    # Backtick-wrapped first: `[[name]]` to placeholder (strips backticks)
    text = re.sub(r"`\[\[(\w+)\]\]`", _sub, text)
    # Then bare: [[name]] to placeholder
    text = re.sub(r"\[\[(\w+)\]\]", _sub, text)
    return text, xrefs


def _restore_xrefs(text: str, xrefs: list[str]) -> str:
    """Restore cross-reference placeholders to ``:f:func:`` roles."""
    for i, name in enumerate(xrefs):
        text = text.replace(f"{_XREF_S}{i}{_XREF_E}", f":f:func:`{name}`")
    return text


def _fix_headings_no_space(text: str) -> str:
    """``##NAME`` to ``## NAME``: CommonMark requires the space.

    Only inserts a space when the character following the ``#`` run is a
    non-space, non-``#`` character (so ``## Title`` is left alone).
    """
    return re.sub(r"^(#{1,6})(?=[^#\s])", r"\1 ", text, flags=re.MULTILINE)


def _split_admonitions(text: str) -> list[tuple[str, str | None]]:
    """Split *text* into ``(content, adm_type | None)`` segments.

    ``adm_type`` is ``None`` for regular Markdown; otherwise a key into
    :data:`_FORD_ADMONITIONS`.
    """
    segments: list[tuple[str, str | None]] = []
    buf: list[str] = []
    in_adm: str | None = None

    def _flush() -> None:
        nonlocal in_adm
        body = "\n".join(buf)
        if body.strip() or in_adm is not None:
            segments.append((body, in_adm))
        buf.clear()
        in_adm = None

    for line in text.split("\n"):
        stripped = line.strip()

        # @endXXX closes a block-form admonition
        if in_adm is not None and _RE_ADM_END.match(stripped):
            _flush()
            continue

        # @note / @warning / … starts an admonition
        start_m = _RE_ADM_START.match(stripped)
        if start_m:
            _flush()  # flush preceding regular content
            in_adm = start_m.group(1).lower()
            adm_text = start_m.group(2).strip()
            if adm_text:
                buf.append(adm_text)
            continue

        # Single-line admonition: blank line ends it
        if in_adm is not None and not stripped:
            _flush()
            buf.append("")  # blank line belongs to the next segment
            continue

        buf.append(line)

    _flush()
    return segments


class _RstRenderer:
    """Walk a *markdown-it-py* token list and produce RST text."""

    def render(self, tokens: list[Any]) -> str:
        lines: list[str] = []
        self._block(tokens, 0, len(tokens), lines, indent="")
        # Strip trailing blank lines
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)

    # -- block-level ---------------------------------------------------------

    def _block(
        self,
        tokens: list[Any],
        start: int,
        end: int,
        out: list[str],
        indent: str,
    ) -> None:
        i = start
        while i < end:
            tok = tokens[i]
            tp = tok.type

            if tp == "heading_open":
                level = int(tok.tag[1])  # "h2" to 2
                title = self._inline(tokens[i + 1].children or [])
                ch = _HEADING_CHARS[min(level - 1, len(_HEADING_CHARS) - 1)]
                out.append("")
                out.append(f"{indent}{title}")
                out.append(f"{indent}{ch * len(title)}")
                out.append("")
                i += 3  # heading_open, inline, heading_close

            elif tp == "paragraph_open":
                hidden = getattr(tok, "hidden", False)
                text = self._inline(tokens[i + 1].children or [])
                for ln in text.split("\n"):
                    # Escape explicit markup starts from plain markdown text
                    # (e.g. ".. todo::") so docutils won't treat them as
                    # directives/targets.
                    if ln.lstrip().startswith(".. "):
                        ln = "\\" + ln
                    out.append(f"{indent}{ln}" if ln else "")
                if not hidden:
                    out.append("")
                i += 3  # paragraph_open, inline, paragraph_close

            elif tp == "fence":
                lang = tok.info.strip() or "text"
                out.append("")
                out.append(f"{indent}.. code-block:: {lang}")
                out.append("")
                for ln in tok.content.rstrip("\n").split("\n"):
                    out.append(f"{indent}   {ln}")
                out.append("")
                i += 1

            elif tp == "code_block":
                out.append("")
                out.append(f"{indent}.. code-block:: text")
                out.append("")
                for ln in tok.content.rstrip("\n").split("\n"):
                    out.append(f"{indent}   {ln}")
                out.append("")
                i += 1

            elif tp == "bullet_list_open":
                j = self._find_close(tokens, i, "bullet_list_close")
                self._list(tokens, i + 1, j, out, indent, ordered=False)
                i = j + 1

            elif tp == "ordered_list_open":
                j = self._find_close(tokens, i, "ordered_list_close")
                self._list(tokens, i + 1, j, out, indent, ordered=True)
                i = j + 1

            elif tp == "blockquote_open":
                j = self._find_close(tokens, i, "blockquote_close")
                self._block(tokens, i + 1, j, out, indent + "   ")
                i = j + 1

            elif tp == "hr":
                out.append("")
                out.append(f"{indent}----")
                out.append("")
                i += 1

            elif tp == "table_open":
                j = self._find_close(tokens, i, "table_close")
                self._table(tokens, i + 1, j, out, indent)
                i = j + 1

            elif tp == "html_block":
                for ln in tok.content.rstrip("\n").split("\n"):
                    out.append(f"{indent}{ln}")
                out.append("")
                i += 1

            else:
                i += 1

    def _list(
        self,
        tokens: list[Any],
        start: int,
        end: int,
        out: list[str],
        indent: str,
        ordered: bool,
    ) -> None:
        marker = "#." if ordered else "*"
        i = start
        while i < end:
            tok = tokens[i]
            if tok.type == "list_item_open":
                j = self._find_close(tokens, i, "list_item_close")
                item_lines: list[str] = []
                self._block(tokens, i + 1, j, item_lines, indent="")
                # Strip surrounding blank lines
                while item_lines and not item_lines[0].strip():
                    item_lines.pop(0)
                while item_lines and not item_lines[-1].strip():
                    item_lines.pop()
                if item_lines:
                    out.append(f"{indent}{marker} {item_lines[0].strip()}")
                    cont = indent + " " * (len(marker) + 1)
                    for ln in item_lines[1:]:
                        out.append(f"{cont}{ln}" if ln else "")
                i = j + 1
            else:
                i += 1

        if out and out[-1] != "":
            out.append("")

    def _inline(self, children: list[Any]) -> str:
        parts: list[str] = []
        i = 0
        while i < len(children):
            tok = children[i]
            tp = tok.type

            if tp == "text":
                text = tok.content
                # RST shortcut references like `name`_ in markdown text are
                # interpreted by docutils and can trigger "Unknown target name"
                # warnings. Treat them as inline code literals instead.
                text = re.sub(r"`([^`]+)`_", r"``\1``", text)
                # Escape trailing underscores in plain words (e.g. "get_",
                # "llvm_", "selected_*_kind") so docutils doesn't treat them
                # as reference targets.
                text = re.sub(r"(?<=\w)_(?=(?:\W|$))", r"\\_", text)
                # Escape literal asterisks/backticks from markdown text so they
                # don't become malformed RST emphasis or interpreted text.
                text = text.replace("*", r"\*")
                text = text.replace("`", r"\`")
                parts.append(text)
                i += 1
            elif tp == "code_inline":
                parts.append(f"``{tok.content}``")
                i += 1
            elif tp == "softbreak":
                parts.append("\n")
                i += 1
            elif tp == "hardbreak":
                parts.append("\n")
                i += 1
            elif tp == "strong_open":
                inner, j = self._collect_until(children, i + 1, "strong_close")
                parts.append(f"**{inner}**")
                i = j + 1
            elif tp == "em_open":
                inner, j = self._collect_until(children, i + 1, "em_close")
                parts.append(f"*{inner}*")
                i = j + 1
            elif tp == "link_open":
                href = tok.attrGet("href") or ""
                inner, j = self._collect_until(children, i + 1, "link_close")
                if href.startswith(("http://", "https://")):
                    parts.append(f"`{inner} <{href}>`_")
                else:
                    parts.append(inner)
                i = j + 1
            elif tp == "image":
                parts.append(tok.content or "")
                i += 1
            elif tp == "html_inline":
                parts.append(tok.content)
                i += 1
            else:
                i += 1
        return "".join(parts)

    def _collect_until(self, children: list[Any], start: int, end_type: str) -> tuple[str, int]:
        """Collect inline content until *end_type*; return (text, end_idx)."""
        sub: list[Any] = []
        i = start
        while i < len(children):
            if children[i].type == end_type:
                return self._inline(sub), i
            sub.append(children[i])
            i += 1
        return self._inline(sub), i

    def _table(
        self,
        tokens: list[Any],
        start: int,
        end: int,
        out: list[str],
        indent: str,
    ) -> None:
        """Render a GFM table as an RST ``.. list-table::`` directive."""
        headers: list[str] = []
        rows: list[list[str]] = []

        i = start
        while i < end:
            tok = tokens[i]

            if tok.type == "thead_open":
                j = self._find_close(tokens, i, "thead_close")
                # Extract header cells
                headers = self._table_row_cells(tokens, i + 1, j)
                i = j + 1

            elif tok.type == "tbody_open":
                j = self._find_close(tokens, i, "tbody_close")
                # Extract body rows
                ri = i + 1
                while ri < j:
                    if tokens[ri].type == "tr_open":
                        rj = self._find_close(tokens, ri, "tr_close")
                        rows.append(self._table_row_cells(tokens, ri + 1, rj))
                        ri = rj + 1
                    else:
                        ri += 1
                i = j + 1
            else:
                i += 1

        # Emit RST list-table
        out.append("")
        out.append(f"{indent}.. list-table::")
        out.append(f"{indent}   :header-rows: 1")
        out.append("")
        if headers:
            out.append(f"{indent}   * - {headers[0]}")
            for cell in headers[1:]:
                out.append(f"{indent}     - {cell}")
        for row in rows:
            if row:
                out.append(f"{indent}   * - {row[0]}")
                for cell in row[1:]:
                    out.append(f"{indent}     - {cell}")
        out.append("")

    def _table_row_cells(self, tokens: list[Any], start: int, end: int) -> list[str]:
        """Extract cell text from a table row (``tr_open`` … ``tr_close``)."""
        cells: list[str] = []
        i = start
        while i < end:
            tok = tokens[i]
            if tok.type in ("th_open", "td_open"):
                close_type = "th_close" if tok.type == "th_open" else "td_close"
                j = self._find_close(tokens, i, close_type)
                # The cell content is in the inline token between open/close
                cell_text = ""
                for ci in range(i + 1, j):
                    if tokens[ci].type == "inline":
                        cell_text = self._inline(tokens[ci].children or [])
                        break
                cells.append(cell_text)
                i = j + 1
            else:
                i += 1
        return cells

    @staticmethod
    def _find_close(tokens: list[Any], start: int, close_type: str) -> int:
        """Find the matching close token accounting for nesting."""
        open_type = tokens[start].type
        depth = 1
        i = start + 1
        while i < len(tokens):
            if tokens[i].type == open_type:
                depth += 1
            elif tokens[i].type == close_type:
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return len(tokens)


_md_parser: MarkdownIt | None = None
_rst_renderer = _RstRenderer()


def _get_parser() -> MarkdownIt:
    global _md_parser
    if _md_parser is None:
        _md_parser = MarkdownIt("commonmark").enable("table")
    return _md_parser


def md_to_rst(lines: list[str] | str | None) -> str:
    """Convert FORD-style Markdown doc comment to RST.

    Parameters
    ----------
    lines
        List of doc comment lines (as returned by FORD), a single string,
        or None.

    Returns
    -------
    str
        RST-formatted text.
    """
    if lines is None:
        return ""
    if isinstance(lines, str):
        text = lines
    else:
        # Preserve leading indentation from FORD doc comments, markdown list
        # and nested block structure depends on it.
        text = "\n".join(line.rstrip() for line in lines)

    if not text.strip():
        return ""

    # ---- pre-process FORD syntax ------------------------------------------
    text, xrefs = _preprocess_xrefs(text)
    text = _fix_headings_no_space(text)

    # ---- split at admonitions and render each segment ---------------------
    segments = _split_admonitions(text)
    md = _get_parser()
    parts: list[str] = []

    for body, adm_type in segments:
        if not body.strip():
            if adm_type is None:
                parts.append("")
            continue

        tokens = md.parse(body)
        rst = _rst_renderer.render(tokens)

        if adm_type is not None:
            directive = _FORD_ADMONITIONS[adm_type]
            parts.append("")
            parts.append(f".. {directive}::")
            parts.append("")
            for ln in rst.split("\n"):
                parts.append(f"   {ln}" if ln.strip() else "")
            parts.append("")
        else:
            parts.append(rst)

    result = "\n".join(parts)

    result = _restore_xrefs(result, xrefs)

    return result
