"""Tests for MD to RST converter."""

from sphinx_ford._md2rst import md_to_rst


class TestMd2Rst:
    def test_none_input(self):
        assert md_to_rst(None) == ""

    def test_empty_list(self):
        assert md_to_rst([]) == ""

    def test_empty_string(self):
        assert md_to_rst("") == ""

    def test_plain_text(self):
        result = md_to_rst(["Hello world"])
        assert "Hello world" in result

    def test_list_of_lines(self):
        result = md_to_rst([" First line", " Second line"])
        assert "First line" in result
        assert "Second line" in result

    def test_ford_crossref(self):
        result = md_to_rst(["See [[my_func]] for details"])
        assert ":f:func:`my_func`" in result

    def test_ford_crossref_multiple(self):
        result = md_to_rst(["Use [[func_a]] and [[func_b]]"])
        assert ":f:func:`func_a`" in result
        assert ":f:func:`func_b`" in result

    def test_heading(self):
        result = md_to_rst(["## My Section"])
        assert "My Section" in result
        assert "----------" in result or "-----" in result

    def test_heading_level1(self):
        result = md_to_rst(["# Title"])
        lines = result.split("\n")
        title_idx = next(i for i, line in enumerate(lines) if "Title" in line)
        assert "=" in lines[title_idx + 1]

    def test_code_block(self):
        result = md_to_rst(["```fortran", "call foo()", "```"])
        assert ".. code-block:: fortran" in result
        assert "   call foo()" in result

    def test_code_block_no_lang(self):
        result = md_to_rst(["```", "some code", "```"])
        assert ".. code-block:: text" in result

    def test_inline_code(self):
        result = md_to_rst(["Use `my_var` here"])
        assert "``my_var``" in result

    def test_unordered_list_dash(self):
        result = md_to_rst(["- item one", "- item two"])
        assert "* item one" in result
        assert "* item two" in result

    def test_unordered_list_star(self):
        result = md_to_rst(["* item one"])
        assert "* item one" in result

    def test_bold_passthrough(self):
        result = md_to_rst(["This is **bold** text"])
        assert "**bold**" in result

    def test_italic_passthrough(self):
        result = md_to_rst(["This is *italic* text"])
        assert "*italic*" in result

    def test_real_ford_doc(self):
        """Test with actual FORD doc comment from toml-f."""
        lines = [
            " Public API for TOML Fortran",
            "",
            " Use [[toml_load]] to load a TOML document from a file.",
            "",
            " ## Parsing TOML",
            "",
            " ```fortran",
            " type(toml_table), allocatable :: table",
            ' call toml_load(table, "config.toml")',
            " ```",
        ]
        result = md_to_rst(lines)
        assert ":f:func:`toml_load`" in result
        assert "Parsing TOML" in result
        assert ".. code-block:: fortran" in result
        assert "call toml_load" in result


class TestAdmonitions:
    """Test FORD admonition conversion."""

    def test_note_single_line(self):
        result = md_to_rst(["@note This is a note."])
        assert ".. note::" in result
        assert "This is a note." in result

    def test_warning_single_line(self):
        result = md_to_rst(["@warning This is deprecated."])
        assert ".. warning::" in result
        assert "This is deprecated." in result

    def test_todo_single_line(self):
        result = md_to_rst(["@todo Implement this."])
        assert ".. note::" in result
        assert "Implement this." in result

    def test_bug_maps_to_danger(self):
        result = md_to_rst(["@bug Known issue with large arrays."])
        assert ".. danger::" in result
        assert "Known issue" in result

    def test_history_maps_to_versionchanged(self):
        result = md_to_rst(["@history Changed in v2.0."])
        assert ".. versionchanged::" in result
        assert "Changed in v2.0." in result

    def test_block_form(self):
        lines = [
            "@note",
            "This is a multi-line",
            "admonition block.",
            "@endnote",
        ]
        result = md_to_rst(lines)
        assert ".. note::" in result
        assert "This is a multi-line" in result
        assert "admonition block." in result
        # Text after @endnote should not be indented
        assert "@endnote" not in result

    def test_note_with_text_after(self):
        lines = [
            "@note Important info",
            "More details here.",
            "@endnote",
            "Regular text.",
        ]
        result = md_to_rst(lines)
        assert ".. note::" in result
        assert "Important info" in result
        assert "More details here." in result
        # "Regular text" should not be inside the admonition
        result_lines = result.split("\n")
        for i, line in enumerate(result_lines):
            if "Regular text" in line:
                assert not line.startswith("   "), "Regular text should not be indented"

    def test_case_insensitive(self):
        result = md_to_rst(["@NOTE This works too."])
        assert ".. note::" in result

    def test_mixed_with_other_content(self):
        lines = [
            "Normal paragraph.",
            "",
            "@warning Be careful!",
            "",
            "More text.",
        ]
        result = md_to_rst(lines)
        assert ".. warning::" in result
        assert "Normal paragraph." in result
        assert "More text." in result


class TestAdmonitionInlineProcessing:
    """Test that inline formatting works inside admonitions (Defect 1a)."""

    def test_admonition_xref(self):
        """[[entity]] inside admonition should become :f:func: role."""
        lines = ["@note See [[my_func]] for details.", "@endnote"]
        result = md_to_rst(lines)
        assert ":f:func:`my_func`" in result

    def test_admonition_inline_code(self):
        """Single backtick code inside admonition should be doubled."""
        lines = ["@note Use `my_var` here.", "@endnote"]
        result = md_to_rst(lines)
        assert "``my_var``" in result

    def test_admonition_list_items(self):
        """List items inside admonitions should be converted."""
        lines = ["@note", "- item one", "- item two", "@endnote"]
        result = md_to_rst(lines)
        assert "* item one" in result
        assert "* item two" in result

    def test_admonition_ends_on_blank_line(self):
        """Single-line admonition ends on blank line."""
        lines = [
            "@note Single-line note content.",
            "",
            "This is NOT in the admonition.",
        ]
        result = md_to_rst(lines)
        assert ".. note::" in result
        result_lines = result.split("\n")
        for line in result_lines:
            if "NOT in the admonition" in line:
                assert not line.startswith("   "), (
                    "Text after blank line should not be in admonition"
                )

    def test_admonition_does_not_swallow_headings(self):
        """Heading after admonition should not be swallowed."""
        lines = [
            "@note Important info.",
            "",
            "## Next Section",
            "Some text.",
        ]
        result = md_to_rst(lines)
        assert ".. note::" in result
        assert "Next Section" in result
        # Heading should not be indented as admonition content
        result_lines = result.split("\n")
        for line in result_lines:
            if "Next Section" in line and line.strip() == "Next Section":
                assert not line.startswith("   ")


class TestBacktickWrappedXrefs:
    """Test backtick-wrapped FORD cross-references (Defect 2)."""

    def test_backtick_xref(self):
        """`[[name]]` to :f:func:`name` (not ``..`` wrapping a role)."""
        result = md_to_rst(["`[[my_func]]`"])
        assert ":f:func:`my_func`" in result
        # Should NOT have doubled backticks around the role
        assert "``" not in result or "`:f:func:" not in result

    def test_backtick_xref_in_sentence(self):
        result = md_to_rst(["Use `[[parse_f_source]]` to parse."])
        assert ":f:func:`parse_f_source`" in result


class TestUnderscoreBold:
    """Test __bold__ to **bold** conversion (Defect 3)."""

    def test_underscore_bold(self):
        result = md_to_rst(["__Target sorting:__ topological sort"])
        assert "**Target sorting:**" in result

    def test_underscore_bold_not_dunder(self):
        """Don't convert __text__ when adjacent to word chars on both sides."""
        # x__init__y should NOT convert (word chars on both sides)
        result = md_to_rst(["x__init__y is special."])
        assert "x__init__y" in result

    def test_underscore_bold_multiple(self):
        result = md_to_rst(["__Source scope:__ and __Target type:__ info"])
        assert "**Source scope:**" in result
        assert "**Target type:**" in result


class TestMarkdownLinks:
    """Test [text](url) to `text <url>`_ conversion (Defect 4)."""

    def test_simple_link(self):
        result = md_to_rst(["See [M_CLI2](https://github.com/urbanjost/M_CLI2)"])
        assert "`M_CLI2 <https://github.com/urbanjost/M_CLI2>`_" in result

    def test_link_in_sentence(self):
        result = md_to_rst(["Uses [Lua API](http://www.lua.org/manual/) for bindings."])
        assert "`Lua API <http://www.lua.org/manual/>`_" in result

    def test_no_false_positive(self):
        """Non-URL brackets should not be converted."""
        result = md_to_rst(["array[i](j)"])
        assert "`" not in result or "array[i](j)" in result


class TestHeadingNoSpace:
    """Test ##HEADING (no space) recognition (Defect 5)."""

    def test_heading_no_space(self):
        result = md_to_rst(["##NAME"])
        result.strip().split("\n")
        # Should produce a heading, not literal ##NAME
        assert "NAME" in result
        assert "##NAME" not in result  # raw ## should be gone

    def test_heading_no_space_level3(self):
        result = md_to_rst(["###SYNOPSIS"])
        assert "SYNOPSIS" in result
        assert "###" not in result

    def test_heading_with_space_still_works(self):
        result = md_to_rst(["## Normal Heading"])
        assert "Normal Heading" in result
        assert "##" not in result


class TestOrderedLists:
    """Test ordered list conversion."""

    def test_ordered_list(self):
        result = md_to_rst(["1. First item", "2. Second item"])
        assert "#. First item" in result
        assert "#. Second item" in result


class TestHeadingInlineProcessing:
    """Test that inline formatting works inside headings."""

    def test_heading_with_backtick_code(self):
        result = md_to_rst(["## Store `compile_commands.json` table"])
        assert "``compile_commands.json``" in result
        assert "Store" in result
        # Should not contain single backticks
        assert "`compile_commands.json`" not in result.replace("``compile_commands.json``", "")

    def test_heading_with_xref(self):
        result = md_to_rst(["## Using [[my_func]]"])
        assert ":f:func:`my_func`" in result


class TestMarkdownTables:
    """Test Markdown table handling."""

    def test_table_no_line_block(self):
        """Markdown table | lines should not produce RST line-blocks."""
        lines = [
            "| Name | Description |",
            "|------|-------------|",
            "| ``success`` | Operation completed |",
        ]
        result = md_to_rst(lines)
        # Should not start with | (which RST interprets as line-block)
        for rline in result.split("\n"):
            stripped = rline.strip()
            if stripped:
                assert not stripped.startswith("|"), (
                    f"Line starts with | (RST line-block): {stripped}"
                )

    def test_table_renders_as_list_table(self):
        """Tables should render as RST list-table directives."""
        lines = [
            "| Name | Value |",
            "|------|-------|",
            "| a    | 1     |",
            "| b    | 2     |",
        ]
        result = md_to_rst(lines)
        assert ".. list-table::" in result
        assert ":header-rows: 1" in result
        assert "Name" in result
        assert "Value" in result

    def test_table_without_leading_pipes(self):
        """GFM tables without leading/trailing pipes should also work."""
        lines = [
            "color | code",
            "------|-----",
            "red   | 31",
            "green | 32",
        ]
        result = md_to_rst(lines)
        assert ".. list-table::" in result
        assert "color" in result
        assert "red" in result


class TestRstSafety:
    """Test conversion safety for docutils-sensitive text patterns."""

    def test_rst_shortcut_reference_is_literalized(self):
        result = md_to_rst(["Call `get`_ to retrieve values."])
        assert "``get``" in result
        assert "`get`_" not in result

    def test_explicit_markup_line_is_escaped(self):
        result = md_to_rst([".. todo::", "", "details"])
        assert "\\.. todo::" in result

    def test_list_followed_by_paragraph_has_blank_line(self):
        result = md_to_rst(["- one", "- two", "", "after list"])
        assert "* one" in result
        assert "* two" in result
        assert "\n\nafter list" in result

    def test_trailing_underscore_word_is_escaped(self):
        result = md_to_rst(["allocated in the get_ routines", "llvm_ wrappers", "selected_*_kind"])
        assert "get\\_ routines" in result
        assert "llvm\\_ wrappers" in result
        assert "selected\\_\\*_kind" in result

    def test_admonition_followed_by_text_has_blank_line(self):
        result = md_to_rst(
            [
                "@note",
                "inside",
                "@endnote",
                "outside",
            ]
        )
        assert ".. note::" in result
        assert "   inside" in result
        assert "\n\noutside" in result
