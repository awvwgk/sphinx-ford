"""FORD bridge: load Fortran source via FORD's internal API.

Provides Sphinx config values:
- ``ford_project_file``: path to a single FORD project file
- ``ford_project_files``: list of FORD project files (string or dict)
- ``ford_project_vars``: dict for @VAR@ substitution in project files
- ``ford_preprocess``: whether to run preprocessor (default True)
- ``ford_case``: normalize Fortran keywords/attributes (``"lower"`` or ``"upper"``)
- ``ford_export_modules_json``: export FORD-compatible modules.json
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective

from sphinx_ford._md2rst import md_to_rst

logger = logging.getLogger(__name__)

# Module-level case normalization setting, set during ``_builder_inited``.
_ford_case: str | None = None


def _normalize_case(text: str) -> str:
    """Normalize case of a Fortran keyword or attribute.

    Uses the module-level ``_ford_case`` setting:
    - ``"lower"``: lowercase everything
    - ``"upper"``: uppercase everything
    - ``None``: preserve as-is
    """
    if _ford_case == "lower":
        return text.lower()
    elif _ford_case == "upper":
        return text.upper()
    return text


def _check_ford():
    """Import ford lazily and check availability."""
    try:
        import ford
    except ImportError:
        raise ExtensionError(
            "sphinx-ford: the 'ford' package is required for the FORD bridge. "
            "Install it with: pip install ford"
        )
    return ford


def _substitute_vars(text: str, variables: Dict[str, str]) -> str:
    """Replace @VAR@ patterns in text with values from variables dict."""
    for key, value in variables.items():
        text = text.replace(f"@{key}@", value)
    return text


def _load_ford_project(
    project_file: str,
    variables: Optional[Dict[str, str]] = None,
    preprocess: bool = True,
) -> Any:
    """Load a FORD project from a project file.

    Supports both FORD 6.x and 7.x via the compatibility layer.

    Returns
    -------
    ford.fortran_project.Project
    """
    _check_ford()

    project_path = Path(project_file).resolve()
    if not project_path.exists():
        raise ExtensionError(f"sphinx-ford: FORD project file not found: {project_path}")

    from sphinx_ford._ford_compat import load_ford_project

    t0 = time.monotonic()
    try:
        project = load_ford_project(project_path, variables, preprocess)
    except SystemExit as e:
        raise ExtensionError(f"sphinx-ford: FORD project loading failed: {e}")

    elapsed = time.monotonic() - t0
    logger.info(
        "sphinx-ford: parsed %d files (%d modules) in %.1fs",
        len(project.files),
        len(project.modules),
        elapsed,
    )

    return project


def _format_type_decl(entity: Any) -> str:
    """Build a Fortran-style type declaration for variables/members.

    Produces RST like: *type* (:f:type:`enum_policy`), *allocatable*
    with cross-reference links and italic keywords.
    """
    vartype = getattr(entity, "vartype", None)
    if not vartype:
        return ""

    vt = _normalize_case(str(vartype))
    vt_lower = vt.lower()
    proto = getattr(entity, "proto", None)
    proto_name = None
    if proto and isinstance(proto, (list, tuple)) and proto[0]:
        proto_name = proto[0]

    if proto_name and vt_lower in ("type", "class"):
        type_part = f"*{vt}* (:f:type:`{proto_name}`)"
    elif proto_name:
        type_part = f"*{vt}({proto_name})*"
    else:
        kind = getattr(entity, "kind", None)
        strlen = getattr(entity, "strlen", None)
        if kind:
            kind_val = kind
            if kind_val.startswith("kind="):
                kind_val = kind_val[5:]
            type_part = f"*{vt}* (:f:var:`{kind_val}`)"
        elif strlen:
            escaped = str(strlen).replace("*", "\\*")
            type_part = f"*{vt}({_normalize_case('len')}={escaped})*"
        else:
            type_part = f"*{vt}*"

    # Append attributes
    attribs = getattr(entity, "attribs", []) or []
    parts = [type_part]
    for attr in attribs:
        parts.append(f"*{_normalize_case(attr)}*")

    return ", ".join(parts)


def _format_param_qualifier(entity: Any) -> str:
    """Build a Fortran-style type qualifier for procedure parameters.

    Produces RST like: *class* (:f:type:`toml_keyval`), *intent(in)*
    with cross-reference links and italic keywords.
    """
    parts: list[str] = []

    vartype = getattr(entity, "vartype", None)
    if vartype:
        vt = _normalize_case(str(vartype))
        vt_lower = vt.lower()
        proto = getattr(entity, "proto", None)
        proto_name = None
        if proto and isinstance(proto, (list, tuple)) and proto[0]:
            proto_name = proto[0]

        if proto_name and vt_lower in ("type", "class"):
            parts.append(f"*{vt}* (:f:type:`{proto_name}`)")
        elif proto_name:
            parts.append(f"*{vt}({proto_name})*")
        else:
            kind = getattr(entity, "kind", None)
            strlen = getattr(entity, "strlen", None)
            if kind:
                kind_val = kind
                if kind_val.startswith("kind="):
                    kind_val = kind_val[5:]
                parts.append(f"*{vt}* (:f:var:`{kind_val}`)")
            elif strlen:
                escaped = str(strlen).replace("*", "\\*")
                parts.append(f"*{vt}({_normalize_case('len')}={escaped})*")
            else:
                parts.append(f"*{vt}*")

    intent = getattr(entity, "intent", None)
    if intent:
        parts.append(f"*{_normalize_case('intent')}({_normalize_case(intent)})*")

    if getattr(entity, "optional", False):
        parts.append(f"*{_normalize_case('optional')}*")

    attribs = getattr(entity, "attribs", []) or []
    for attr in attribs:
        parts.append(f"*{_normalize_case(attr)}*")

    return ", ".join(parts)


# Maximum length for initial values displayed in signatures
_MAX_INITIAL_LEN = 60


def _format_initial_value(value: str) -> str:
    """Clean and truncate a variable's initial value for display.

    - Replaces HTML entities (``&nbsp;``, ``&amp;``, etc.) with their text
    - Truncates long values (arrays, string literals) with ``...``
    """
    import html

    value = html.unescape(value)
    if len(value) > _MAX_INITIAL_LEN:
        value = value[:_MAX_INITIAL_LEN].rstrip() + "..."
    return value


def _ford_entity_to_rst(
    entity: Any,
    entity_type: str,
    module_name: Optional[str] = None,
    indent: str = "",
    module_procs: Optional[dict[str, str]] = None,
    mod_funcs: Optional[dict[str, Any]] = None,
    mod_subs: Optional[dict[str, Any]] = None,
    visibility: set[str] | None = None,
) -> List[str]:
    """Convert a single FORD entity to RST directive lines."""
    lines: List[str] = []
    name = entity.name

    # Build the directive with signature
    if entity_type in ("function", "subroutine"):
        args = ", ".join(a.name for a in getattr(entity, "args", []))
        # Include attributes (pure, elemental) in display
        attribs = getattr(entity, "attribs", []) or []
        prefix_parts = []
        for attr in attribs:
            if attr.lower() in ("pure", "elemental", "impure", "recursive", "module"):
                prefix_parts.append(_normalize_case(attr))
        prefix = " ".join(prefix_parts)
        if prefix:
            lines.append(f"{indent}.. f:{entity_type}:: {prefix} {name}({args})")
        else:
            lines.append(f"{indent}.. f:{entity_type}:: {name}({args})")
    else:
        # For variables/members, append default value to the signature
        initial = getattr(entity, "initial", None)
        if initial and entity_type in ("variable", "member"):
            init_str = _format_initial_value(str(initial))
            lines.append(f"{indent}.. f:{entity_type}:: {name} = {init_str}")
        else:
            lines.append(f"{indent}.. f:{entity_type}:: {name}")

    # Options
    if module_name:
        lines.append(f"{indent}   :module: {module_name}")

    permission = getattr(entity, "permission", None)
    if permission:
        lines.append(f"{indent}   :permission: {permission}")

    # Detect parameter attribute for variables
    if entity_type == "variable":
        is_param = getattr(entity, "parameter", False)
        if not is_param:
            attribs = getattr(entity, "attribs", []) or []
            is_param = "parameter" in [a.lower() for a in attribs]
        if is_param:
            lines.append(f"{indent}   :parameter:")

    if entity_type == "type":
        extends = getattr(entity, "extends", None)
        if extends and isinstance(extends, str):
            lines.append(f"{indent}   :extends: {extends}")
        if getattr(entity, "abstract", False):
            lines.append(f"{indent}   :abstract:")

    if entity_type == "interface":
        if getattr(entity, "generic", False):
            lines.append(f"{indent}   :generic:")
        if getattr(entity, "abstract", False):
            lines.append(f"{indent}   :abstract:")

    if entity_type == "boundproc":
        if getattr(entity, "deferred", False):
            lines.append(f"{indent}   :deferred:")

    lines.append(f"{indent}")

    # Binding links for bound procedures
    expand_procs: list[tuple[Any, str]] = []
    if entity_type == "boundproc" and module_procs and module_name:
        bindings = getattr(entity, "bindings", []) or []
        if bindings:
            # Separate visible (linkable) and hidden (expand inline) bindings
            link_refs = []
            expand_procs = []
            for bname in bindings:
                proc_kind = module_procs.get(bname.lower())
                if proc_kind not in ("function", "subroutine"):
                    continue
                # Look up the actual procedure object
                proc_obj = None
                if mod_funcs and bname.lower() in mod_funcs:
                    proc_obj = mod_funcs[bname.lower()]
                elif mod_subs and bname.lower() in mod_subs:
                    proc_obj = mod_subs[bname.lower()]
                if proc_obj and _is_visible(proc_obj, visibility):
                    link_refs.append(f":f:func:`{bname} <{module_name}.{bname}>`")
                elif proc_obj:
                    expand_procs.append((proc_obj, proc_kind))
            if link_refs:
                lines.append(f"{indent}   *Binds to:* {', '.join(link_refs)}")
                lines.append(f"{indent}")

    # Doc comment
    doc = getattr(entity, "doc", None)
    if doc:
        rst_doc = md_to_rst(doc)
        if rst_doc.strip():
            for doc_line in rst_doc.split("\n"):
                lines.append(f"{indent}   {doc_line}")
            lines.append(f"{indent}")

    # Inline expansion for bound procedures binding to hidden targets
    if entity_type == "boundproc" and expand_procs:
        for proc_obj, proc_kind in expand_procs:
            # Use the procedure's doc if the bound proc itself had no doc
            if not doc:
                proc_doc = getattr(proc_obj, "doc", None)
                if proc_doc:
                    rst_doc = md_to_rst(proc_doc)
                    if rst_doc.strip():
                        for doc_line in rst_doc.split("\n"):
                            lines.append(f"{indent}   {doc_line}")
                        lines.append(f"{indent}")

            # Emit argument documentation from the procedure
            proc_args = getattr(proc_obj, "args", [])
            if proc_args:
                lines.append(f"{indent}   **Arguments:**")
                lines.append(f"{indent}")

            for arg in proc_args:
                qualifier = _format_param_qualifier(arg)
                arg_doc = getattr(arg, "doc", None)
                doc_text = md_to_rst(arg_doc).strip().replace("\n", " ") if arg_doc else ""

                if qualifier and doc_text:
                    lines.append(f"{indent}   * {qualifier} :: **{arg.name}** — {doc_text}")
                elif qualifier:
                    lines.append(f"{indent}   * {qualifier} :: **{arg.name}**")
                elif doc_text:
                    lines.append(f"{indent}   * **{arg.name}** — {doc_text}")
                else:
                    lines.append(f"{indent}   * **{arg.name}**")

            if proc_args:
                lines.append(f"{indent}")

            # Return value for functions
            if proc_kind == "function":
                retvar = getattr(proc_obj, "retvar", None)
                if retvar:
                    ret_qual = _format_param_qualifier(retvar)
                    if ret_qual:
                        lines.append(f"{indent}   **Returns:** {ret_qual}")
                        lines.append(f"{indent}")

    # Variable/member type declaration
    if entity_type in ("variable", "member"):
        type_decl = _format_type_decl(entity)
        if type_decl:
            lines.append(f"{indent}   **Type:** {type_decl}")
            lines.append(f"{indent}")

    # Argument documentation for procedures
    if entity_type in ("function", "subroutine"):
        if getattr(entity, "args", []):
            lines.append(f"{indent}   **Arguments:**")
            lines.append(f"{indent}")

        for arg in getattr(entity, "args", []):
            qualifier = _format_param_qualifier(arg)

            # Build the parameter entry in Fortran-like syntax:
            # type(...), intent(in) :: name — description
            arg_doc = getattr(arg, "doc", None)
            doc_text = md_to_rst(arg_doc).strip().replace("\n", " ") if arg_doc else ""

            if qualifier and doc_text:
                lines.append(f"{indent}   * {qualifier} :: **{arg.name}** — {doc_text}")
            elif qualifier:
                lines.append(f"{indent}   * {qualifier} :: **{arg.name}**")
            elif doc_text:
                lines.append(f"{indent}   * **{arg.name}** — {doc_text}")
            else:
                lines.append(f"{indent}   * **{arg.name}**")

        if getattr(entity, "args", []):
            lines.append(f"{indent}")

        # Return value for functions
        if entity_type == "function":
            retvar = getattr(entity, "retvar", None)
            if retvar:
                ret_qual = _format_param_qualifier(retvar)
                if ret_qual:
                    lines.append(f"{indent}   **Returns:** {ret_qual}")
                    lines.append(f"{indent}")

        lines.append(f"{indent}")

    return lines


def _emit_modprocs(
    modprocs: list,
    mod_name: str,
    mod_funcs: dict,
    mod_subs: dict,
    emitted_proc_fqns: set[str],
    lines: List[str],
    indent: str,
    visibility: set[str] | None = None,
) -> None:
    """Emit resolved modproc procedures as RST directives.

    Resolves modproc references against the module's functions/subroutines
    and emits them with full signatures.  Tracks emitted FQNs to avoid
    duplicates when the same proc appears in multiple interfaces.
    """
    for mp in modprocs:
        mp_name = getattr(mp, "name", None)
        if not mp_name:
            continue
        proc_fqn = f"{mod_name.lower()}.{mp_name.lower()}"
        if proc_fqn in emitted_proc_fqns:
            continue
        emitted_proc_fqns.add(proc_fqn)
        resolved = mod_funcs.get(mp_name.lower()) or mod_subs.get(mp_name.lower())
        if resolved:
            if not _is_visible(resolved, visibility):
                continue
            mp_type = "function" if getattr(resolved, "retvar", None) else "subroutine"
            lines.extend(_ford_entity_to_rst(resolved, mp_type, mod_name, indent=indent))
        else:
            mp_entity = getattr(mp, "procedure", mp)
            if hasattr(mp_entity, "name"):
                if not _is_visible(mp_entity, visibility):
                    continue
                mp_type = "function" if getattr(mp_entity, "retvar", None) else "subroutine"
                lines.extend(_ford_entity_to_rst(mp_entity, mp_type, mod_name, indent=indent))


def _parse_visibility(directive_opt: str | None, default: set[str] | None) -> set[str] | None:
    """Parse a visibility option into a set of permission levels.

    The directive option is a comma-separated string like ``"public, protected"``.
    Falls back to the project-level default if not specified.  Returns None
    if no filtering should be applied.
    """
    if directive_opt is not None:
        return {v.strip().lower() for v in directive_opt.split(",") if v.strip()}
    return default


def _is_visible(entity: Any, visibility: set[str] | None) -> bool:
    """Check whether an entity should be shown given the visibility filter."""
    if visibility is None:
        return True
    perm = getattr(entity, "permission", "public")
    return (perm or "public").lower() in visibility


def _module_to_rst(
    module: Any,
    visibility: set[str] | None = None,
    available_module_names: set[str] | None = None,
) -> List[str]:
    """Convert a FORD module to RST lines.

    Parameters
    ----------
    module
        FORD module object.
    visibility
        Set of permission levels to include (e.g. {"public", "protected"}).
        If None, all entities are shown regardless of permission.
    """
    lines: List[str] = []
    mod_name = module.name

    lines.append(f".. f:module:: {mod_name}")

    permission = getattr(module, "permission", None)
    if permission:
        lines.append(f"   :permission: {permission}")

    lines.append("")

    # Module doc
    doc = getattr(module, "doc", None)
    if doc:
        rst_doc = md_to_rst(doc)
        if rst_doc.strip():
            for doc_line in rst_doc.split("\n"):
                lines.append(f"   {doc_line}")
            lines.append("")

    # Uses (module dependencies)
    uses = getattr(module, "uses", []) or []
    if uses:
        use_names = []
        seen_use_names: set[str] = set()
        for u in uses:
            dep = u[0] if isinstance(u, (list, tuple)) else u
            if isinstance(dep, str):
                dep_name = dep
            elif hasattr(dep, "name"):
                dep_name = dep.name
            else:
                continue

            key = dep_name.lower()
            if key in seen_use_names:
                continue
            seen_use_names.add(key)
            use_names.append(dep_name)
        if use_names:
            # Only emit cross-references for modules that exist in the parsed
            # FORD module list; missing modules (e.g. parser gaps) are shown
            # as plain text to avoid unresolved xrefs.
            available_module_names = available_module_names or set()
            rendered_uses = [
                (f":f:mod:`{n}`" if n.lower() in available_module_names else n) for n in use_names
            ]
            lines.append(f"   **Uses:** {', '.join(rendered_uses)}")
            lines.append("")

    # Build lookup dicts for resolving interface modprocs to actual procedures
    mod_funcs = {f.name.lower(): f for f in getattr(module, "functions", [])}
    mod_subs = {s.name.lower(): s for s in getattr(module, "subroutines", [])}

    # Collect procedure names that belong to interfaces (to skip at module level)
    # Also collect interface names themselves (functions with the same name as
    # an interface should be shown under the interface, not at module level).
    interface_proc_names: set[str] = set()
    interface_names: set[str] = set()
    for iface in getattr(module, "interfaces", []):
        interface_names.add(iface.name.lower())
        for mp in getattr(iface, "modprocs", []) or []:
            if hasattr(mp, "name"):
                interface_proc_names.add(mp.name.lower())

    # Track already-emitted proc FQNs to avoid duplicates when the same
    # procedure appears in modprocs of multiple interfaces.
    emitted_proc_fqns: set[str] = set()

    # Variables: deduplicate by name (FORD can emit duplicates from
    # #ifdef/#else branches)
    seen_var_names: set[str] = set()
    for var in getattr(module, "variables", []):
        vname = var.name.lower()
        if vname in seen_var_names:
            continue
        seen_var_names.add(vname)
        if not _is_visible(var, visibility):
            continue
        lines.extend(_ford_entity_to_rst(var, "variable", mod_name, indent="   "))

    # Build merged interface dict (handles FORD duplicate interface names)
    from collections import OrderedDict

    merged_ifaces: OrderedDict[str, list] = OrderedDict()
    for iface in getattr(module, "interfaces", []):
        key = iface.name.lower()
        if key not in merged_ifaces:
            merged_ifaces[key] = (iface, [])
        for mp in getattr(iface, "modprocs", []) or []:
            merged_ifaces[key][1].append(mp)

    # Identify constructor interfaces (interface name == type name)
    type_names = {t.name.lower() for t in getattr(module, "types", [])}
    constructor_iface_names: set[str] = set()
    for key in merged_ifaces:
        if key in type_names:
            constructor_iface_names.add(key)

    # Types
    for typ in getattr(module, "types", []):
        if not _is_visible(typ, visibility):
            continue
        lines.extend(_ford_entity_to_rst(typ, "type", mod_name, indent="   "))

        # Type components: use "member" directive instead of "variable"
        for comp in getattr(typ, "variables", []):
            if not _is_visible(comp, visibility):
                continue
            lines.extend(_ford_entity_to_rst(comp, "member", mod_name, indent="      "))
        # Build module procedure lookup for binding links
        module_procs = {
            **{n: "function" for n in mod_funcs},
            **{n: "subroutine" for n in mod_subs},
        }
        for bp in getattr(typ, "boundprocs", []):
            if not _is_visible(bp, visibility):
                continue
            lines.extend(
                _ford_entity_to_rst(
                    bp,
                    "boundproc",
                    mod_name,
                    indent="      ",
                    module_procs=module_procs,
                    mod_funcs=mod_funcs,
                    mod_subs=mod_subs,
                    visibility=visibility,
                )
            )

        # Constructor interface: emit as part of the type if one exists
        typ_lower = typ.name.lower()
        if typ_lower in constructor_iface_names:
            ctor_iface, ctor_modprocs = merged_ifaces[typ_lower]
            lines.append("      **Constructors:**")
            lines.append("")
            _emit_modprocs(
                ctor_modprocs,
                mod_name,
                mod_funcs,
                mod_subs,
                emitted_proc_fqns,
                lines,
                indent="      ",
                visibility=visibility,
            )

    # Interfaces: skip constructor interfaces (already shown under types)
    for _key, (iface, all_modprocs) in merged_ifaces.items():
        if _key in constructor_iface_names:
            continue
        if not _is_visible(iface, visibility):
            continue
        lines.extend(_ford_entity_to_rst(iface, "interface", mod_name, indent="   "))
        _emit_modprocs(
            all_modprocs,
            mod_name,
            mod_funcs,
            mod_subs,
            emitted_proc_fqns,
            lines,
            indent="      ",
            visibility=visibility,
        )

    # Functions: skip those already shown under interfaces
    # Also skip functions whose name matches an interface name (Cat 4)
    skip_funcs = interface_proc_names | interface_names
    for func in getattr(module, "functions", []):
        if func.name.lower() not in skip_funcs:
            if not _is_visible(func, visibility):
                continue
            lines.extend(_ford_entity_to_rst(func, "function", mod_name, indent="   "))

    # Subroutines (skip those already shown under interfaces)
    skip_subs = interface_proc_names | interface_names
    for sub in getattr(module, "subroutines", []):
        if sub.name.lower() not in skip_subs:
            if not _is_visible(sub, visibility):
                continue
            lines.extend(_ford_entity_to_rst(sub, "subroutine", mod_name, indent="   "))

    lines.append("")
    return lines


class FordAutoModuleDirective(SphinxDirective):
    """Directive to auto-document a Fortran module from FORD sources.

    Usage::

        .. f:automodule:: module_name

    Requires ``ford_project_file`` to be set in conf.py.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "visibility": directives.unchanged,
        "case": directives.unchanged,
    }

    def run(self):
        module_name = self.arguments[0].strip()
        env = self.state.document.settings.env

        project = getattr(env.app, "_ford_project", None)
        if project is None:
            raise ExtensionError(
                "sphinx-ford: f:automodule requires ford_project_file to be set in conf.py"
            )

        # Determine visibility filter
        visibility = _parse_visibility(
            self.options.get("visibility"),
            getattr(env.app, "_ford_display", None),
        )

        # Find the module
        target_mod = None
        for mod in project.modules:
            if mod.name.lower() == module_name.lower():
                target_mod = mod
                break

        if target_mod is None:
            logger.warning("sphinx-ford: module '%s' not found in FORD project", module_name)
            return []

        # Apply per-directive case override
        global _ford_case
        saved_case = _ford_case
        case_opt = self.options.get("case")
        if case_opt is not None:
            _ford_case = case_opt.strip().lower() or None

        try:
            # Generate RST
            available_module_names = {m.name.lower() for m in project.modules}
            rst_lines = _module_to_rst(
                target_mod,
                visibility=visibility,
                available_module_names=available_module_names,
            )
        finally:
            _ford_case = saved_case

        # Parse the RST into a container and return its children
        container = nodes.container()
        vl = StringList(rst_lines, source=f"<ford:{module_name}>")
        self.state.nested_parse(vl, 0, container)

        return container.children


class FordAutoProjectDirective(SphinxDirective):
    """Directive to auto-document all modules from a FORD project.

    Usage::

        .. f:autoproject::

    Requires ``ford_project_file`` to be set in conf.py.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        "visibility": directives.unchanged,
        "case": directives.unchanged,
    }

    def run(self):
        env = self.state.document.settings.env

        project = getattr(env.app, "_ford_project", None)
        if project is None:
            raise ExtensionError(
                "sphinx-ford: f:autoproject requires ford_project_file to be set in conf.py"
            )

        # Determine visibility filter
        visibility = _parse_visibility(
            self.options.get("visibility"),
            getattr(env.app, "_ford_display", None),
        )

        # Apply per-directive case override
        global _ford_case
        saved_case = _ford_case
        case_opt = self.options.get("case")
        if case_opt is not None:
            _ford_case = case_opt.strip().lower() or None

        try:
            # Generate RST for all modules
            rst_lines: List[str] = []
            available_module_names = {m.name.lower() for m in project.modules}
            for mod in sorted(project.modules, key=lambda m: m.name.lower()):
                rst_lines.extend(
                    _module_to_rst(
                        mod,
                        visibility=visibility,
                        available_module_names=available_module_names,
                    )
                )
        finally:
            _ford_case = saved_case

        # Parse the RST into a container and return its children
        container = nodes.container()
        vl = StringList(rst_lines, source="<ford:autoproject>")
        self.state.nested_parse(vl, 0, container)

        return container.children


class _MergedProject:
    """A combined view of multiple FORD projects' modules."""

    def __init__(self):
        self.modules = []
        self.files = []
        self.display: set[str] = set()

    def add_project(self, project: Any) -> None:
        self.modules.extend(project.modules)
        self.files.extend(project.files)
        for val in getattr(project, "display", []) or []:
            self.display.add(val.lower())


def _builder_inited(app: Sphinx) -> None:
    """Load FORD project(s) at build start if configured."""
    app._ford_project = None

    # Support both single file and list of files
    project_files = app.config.ford_project_files or []
    single_file = app.config.ford_project_file
    if single_file and single_file not in project_files:
        project_files = [single_file] + list(project_files)

    if not project_files:
        return

    merged = _MergedProject()

    for entry in project_files:
        # Each entry can be a string path or a dict with path + overrides
        if isinstance(entry, dict):
            pfile = entry["path"]
            pvars = entry.get("vars", {})
            ppreprocess = entry.get("preprocess", app.config.ford_preprocess)
        else:
            pfile = entry
            pvars = app.config.ford_project_vars or {}
            ppreprocess = app.config.ford_preprocess

        try:
            project = _load_ford_project(pfile, pvars, ppreprocess)
            merged.add_project(project)
            logger.info(
                "sphinx-ford: loaded %s (%d modules)",
                pfile,
                len(project.modules),
            )
        except ExtensionError:
            raise
        except Exception as e:
            logger.warning("sphinx-ford: failed to load %s: %s", pfile, e)

    app._ford_project = merged

    # Extract default visibility from the FORD project's display setting,
    # or use the user's ford_display config override.
    user_display = app.config.ford_display
    if user_display:
        app._ford_display = {v.strip().lower() for v in user_display}
    elif merged.display:
        app._ford_display = merged.display
    else:
        app._ford_display = None

    # Set case normalization
    global _ford_case
    _ford_case = app.config.ford_case


def _build_finished(app: Sphinx, exception: Any) -> None:
    """Export FORD-compatible modules.json after build completes."""
    if exception:
        return

    if not app.config.ford_export_modules_json:
        return

    # Only export for HTML-like builders
    if not hasattr(app.builder, "get_target_uri"):
        return

    from sphinx_ford.ford_parser import write_ford_modules_json

    domain = app.env.get_domain("f")
    output_path = Path(app.outdir) / "modules.json"
    try:
        write_ford_modules_json(domain, output_path, app.builder)
    except Exception as e:
        logger.warning("sphinx-ford: failed to export modules.json: %s", e)


def setup(app: Sphinx) -> None:
    """Register FORD bridge config values and directives."""
    app.add_config_value("ford_project_file", None, "env")
    app.add_config_value("ford_project_files", [], "env")
    app.add_config_value("ford_project_vars", {}, "env")
    app.add_config_value("ford_preprocess", True, "env")
    app.add_config_value("ford_display", None, "env")
    app.add_config_value("ford_case", None, "env")
    app.add_config_value("ford_export_modules_json", False, "env")

    app.add_directive("f:automodule", FordAutoModuleDirective)
    app.add_directive("f:autoproject", FordAutoProjectDirective)

    app.connect("builder-inited", _builder_inited)
    app.connect("build-finished", _build_finished)
