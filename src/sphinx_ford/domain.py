"""Fortran domain for Sphinx."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

from docutils import nodes
from docutils.nodes import Element, Node
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.addnodes import desc_signature, pending_xref
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, IndexEntry, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.roles import XRefRole
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.nodes import make_refnode

logger = logging.getLogger(__name__)


class FortranObject(ObjectDescription):
    """Base class for Fortran object directives."""

    option_spec = {
        "module": directives.unchanged,
        "permission": directives.unchanged,
        "noindex": directives.flag,
        "noindexentry": directives.flag,
    }

    # Subclasses set this
    objtype: str = ""

    def get_display_prefix(self) -> List[Node]:
        """Return nodes to prepend to the signature (e.g., 'module ')."""
        return [
            addnodes.desc_annotation("", self.objtype + " "),
        ]

    # Fortran procedure attributes that may prefix a signature
    _FORTRAN_ATTRS = frozenset(
        {
            "pure",
            "elemental",
            "impure",
            "recursive",
            "module",
        }
    )

    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        """Parse the signature and populate signode."""
        sig = sig.strip()

        # Extract leading Fortran attributes (pure, elemental, etc.)
        words = sig.split()
        attrs = []
        while words and words[0].lower() in self._FORTRAN_ATTRS:
            attrs.append(words.pop(0))
        sig = " ".join(words)

        # Extract default value early: "name = value" as name part, value part
        # Must happen before paren search so parens inside default values
        # (e.g. "'((i0))'") are not mistaken for argument lists.
        default_value = ""
        if " = " in sig:
            sig, default_value = sig.split(" = ", 1)
            sig = sig.strip()
            default_value = default_value.strip()

        # Extract the name (first word / token up to '(')
        # Special handling for operator(...) and assignment(=)
        # the parenthesized symbol is part of the name, not an argument list.
        op_match = re.match(r"^(operator|assignment)\s*(\([^)]*\))", sig, re.IGNORECASE)
        if op_match:
            name = op_match.group(1) + op_match.group(2)  # e.g. "operator(==)"
            args_str = sig[op_match.end() :].strip()
            if args_str and not args_str.startswith("("):
                args_str = ""
        else:
            paren_idx = sig.find("(")
            if paren_idx >= 0:
                name = sig[:paren_idx].strip()
                args_str = sig[paren_idx:]
            else:
                name = sig
                args_str = ""

        # Emit: "pure elemental function name(args)"
        # Attributes come first, then the objtype, then the name
        if attrs:
            signode += addnodes.desc_annotation("", " ".join(attrs) + " ")

        for prefix_node in self.get_display_prefix():
            signode += prefix_node

        # Determine the module context
        modname = self.options.get("module") or self.env.ref_context.get("f:module")

        signode["module"] = modname or ""
        signode["fullname"] = name

        # Add the name
        signode += addnodes.desc_name(name, name)

        # Add default value if present (e.g., "member stype = -1_i1")
        if default_value:
            signode += addnodes.desc_annotation("", f" = {default_value}")

        # Add parameters if present
        if args_str:
            # Strip outer parens, desc_parameterlist adds its own
            inner = args_str.strip()
            if inner.startswith("(") and inner.endswith(")"):
                inner = inner[1:-1]
            signode += addnodes.desc_parameterlist(inner, inner)

        return name

    def _get_fqn(self, name: str) -> str:
        """Build the fully-qualified name for storage (lowercase).

        Builds from context stack: module.type.name or module.name.
        """
        parts = []
        modname = self.options.get("module") or self.env.ref_context.get("f:module")
        typename = self.env.ref_context.get("f:type")
        if modname:
            parts.append(modname.lower())
        if typename:
            parts.append(typename.lower())
        parts.append(name.lower())
        return ".".join(parts)

    def add_target_and_index(self, name: str, sig: str, signode: desc_signature) -> None:
        """Add cross-reference target and index entry."""
        fqn = self._get_fqn(name)
        node_id = f"f-{self.objtype}-{fqn}".replace(".", "-")

        signode["ids"].append(node_id)
        self.state.document.note_explicit_target(signode)

        domain: FortranDomain = self.env.get_domain("f")
        domain.note_object(fqn, name, self.objtype, node_id, location=signode)

        if "noindexentry" not in self.options:
            indextext = f"{name} ({self.objtype})"
            self.indexnode["entries"].append(("single", indextext, node_id, "", None))

    def before_content(self) -> None:
        """Push context for nested directives."""
        pass

    def after_content(self) -> None:
        """Pop context after nested content."""
        pass


class FortranModule(FortranObject):
    """Directive for Fortran modules: ``.. f:module:: name``.

    Like the C++ domain, the module signature is rendered prominently
    via the ``desc`` / ``desc_signature`` node structure.  The visual
    heading appearance comes from CSS on ``.sig.sig-object``.
    """

    objtype = "module"

    def before_content(self) -> None:
        """Push module name into ref_context for nested directives."""
        name = self.names[-1] if self.names else None
        if name:
            # Save previous context for nesting
            self.env.ref_context.setdefault("f:module_stack", []).append(
                self.env.ref_context.get("f:module")
            )
            self.env.ref_context["f:module"] = name
            # Clear type context when entering a new module
            self.env.ref_context.pop("f:type", None)

    def after_content(self) -> None:
        """Pop module context."""
        stack = self.env.ref_context.get("f:module_stack", [])
        if stack:
            prev = stack.pop()
            if prev is None:
                self.env.ref_context.pop("f:module", None)
            else:
                self.env.ref_context["f:module"] = prev
        else:
            self.env.ref_context.pop("f:module", None)

    def _get_fqn(self, name: str) -> str:
        """Modules are top-level, no parent prefix."""
        return name.lower()

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        """Provide hierarchy parts so Sphinx can create TOC object entries."""
        fullname = sig_node.get("fullname")
        if not fullname:
            return ()
        return (fullname,)

    def _toc_entry_name(self, sig_node: desc_signature) -> str:
        """Return the TOC entry text for module signatures."""
        if not sig_node.get("_toc_parts"):
            return ""

        name = sig_node.get("fullname") or sig_node["_toc_parts"][-1]
        if self.config.toc_object_entries_show_parents in {"domain", "hide", "all"}:
            return name
        return ""


class FortranCurrentModule(ObjectDescription):
    """Directive to set the current module context without output.

    ``.. f:currentmodule:: name``
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self) -> List[Node]:
        modname = self.arguments[0].strip()
        if modname == "None":
            self.env.ref_context.pop("f:module", None)
        else:
            self.env.ref_context["f:module"] = modname
        return []


class FortranProgram(FortranObject):
    objtype = "program"

    def _get_fqn(self, name: str) -> str:
        return name.lower()


class FortranFunction(FortranObject):
    objtype = "function"

    doc_field_types = [
        TypedField(
            "parameter",
            names=("param", "p", "argument", "arg"),
            typerolename="type",
            typenames=("ftype",),
            label="Parameters",
            can_collapse=True,
        ),
        GroupedField(
            "intent",
            names=("intent",),
            label="Intent",
            can_collapse=True,
        ),
        GroupedField(
            "optional",
            names=("optional",),
            label="Optional",
            can_collapse=True,
        ),
        Field("returnvalue", names=("returns", "return"), label="Returns"),
        Field("returntype", names=("rtype",), label="Return type"),
    ]

    def get_display_prefix(self) -> List[Node]:
        return [addnodes.desc_annotation("", "function ")]


class FortranSubroutine(FortranObject):
    objtype = "subroutine"

    doc_field_types = FortranFunction.doc_field_types.copy()

    def get_display_prefix(self) -> List[Node]:
        return [addnodes.desc_annotation("", "subroutine ")]


class FortranType(FortranObject):
    objtype = "type"

    option_spec = {
        **FortranObject.option_spec,
        "extends": directives.unchanged,
        "abstract": directives.flag,
    }

    def get_display_prefix(self) -> List[Node]:
        if "abstract" in self.options:
            return [addnodes.desc_annotation("", "abstract type ")]
        return super().get_display_prefix()

    def handle_signature(self, sig: str, signode: desc_signature) -> str:
        name = super().handle_signature(sig, signode)
        extends = self.options.get("extends")
        if extends:
            # Build ", extends(" as annotation, then  a pending xref for the
            # parent type name, then closing ")".
            signode += addnodes.desc_annotation("", ", extends(")
            refnode = addnodes.pending_xref(
                "",
                nodes.Text(extends),
                refdomain="f",
                reftype="type",
                reftarget=extends,
            )
            signode += refnode
            signode += addnodes.desc_annotation("", ")")
        return name

    def _get_fqn(self, name: str) -> str:
        """Types use module context but NOT the parent type context."""
        modname = self.options.get("module") or self.env.ref_context.get("f:module")
        if modname:
            return f"{modname.lower()}.{name.lower()}"
        return name.lower()

    def before_content(self) -> None:
        name = self.names[-1] if self.names else None
        if name:
            self.env.ref_context.setdefault("f:type_stack", []).append(
                self.env.ref_context.get("f:type")
            )
            self.env.ref_context["f:type"] = name

    def after_content(self) -> None:
        stack = self.env.ref_context.get("f:type_stack", [])
        if stack:
            prev = stack.pop()
            if prev is None:
                self.env.ref_context.pop("f:type", None)
            else:
                self.env.ref_context["f:type"] = prev
        else:
            self.env.ref_context.pop("f:type", None)


class FortranVariable(FortranObject):
    objtype = "variable"

    option_spec = {
        **FortranObject.option_spec,
        "parameter": directives.flag,
    }

    def get_display_prefix(self):
        if "parameter" in self.options:
            return [addnodes.desc_annotation("", "parameter ")]
        return super().get_display_prefix()


class FortranMember(FortranObject):
    """Type component (data member of a derived type).

    Like C++ ``member``, this is for variables that are part of a type
    definition rather than module-level variables.
    """

    objtype = "member"


class FortranInterface(FortranObject):
    objtype = "interface"

    option_spec = {
        **FortranObject.option_spec,
        "generic": directives.flag,
        "abstract": directives.flag,
    }

    def get_display_prefix(self) -> List[Node]:
        if "abstract" in self.options:
            return [addnodes.desc_annotation("", "abstract interface ")]
        return super().get_display_prefix()


class FortranSubmodule(FortranObject):
    objtype = "submodule"

    def _get_fqn(self, name: str) -> str:
        return name.lower()


class FortranEnum(FortranObject):
    objtype = "enum"


class FortranBoundProcedure(FortranObject):
    objtype = "boundproc"

    option_spec = {
        **FortranObject.option_spec,
        "deferred": directives.flag,
        "generic": directives.flag,
    }

    def get_display_prefix(self) -> List[Node]:
        return [addnodes.desc_annotation("", "procedure ")]


class FortranBlockData(FortranObject):
    objtype = "blockdata"

    def _get_fqn(self, name: str) -> str:
        return name.lower()


class FortranCommon(FortranObject):
    objtype = "common"


class FortranNamelist(FortranObject):
    objtype = "namelist"


class FortranXRefRole(XRefRole):
    """Cross-reference role for Fortran entities."""

    pass


class FortranModuleIndex(Index):
    """Index of all Fortran modules."""

    name = "modindex"
    localname = "Fortran Module Index"
    shortname = "modules"

    def generate(
        self, docnames: Optional[List[str]] = None
    ) -> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
        content: Dict[str, List[IndexEntry]] = {}
        domain: FortranDomain = self.domain

        for fqn, obj in sorted(domain.objects.items()):
            if obj.objtype != "module":
                continue
            if docnames and obj.docname not in docnames:
                continue

            letter = obj.dispname[0].upper()
            entries = content.setdefault(letter, [])
            entries.append(IndexEntry(obj.dispname, 0, obj.docname, obj.node_id, "", "", ""))

        sorted_content = sorted(content.items())
        return sorted_content, True


class FortranProcedureIndex(Index):
    """Index of all Fortran procedures (functions and subroutines)."""

    name = "procindex"
    localname = "Fortran Procedure Index"
    shortname = "procedures"

    def generate(
        self, docnames: Optional[List[str]] = None
    ) -> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
        content: Dict[str, List[IndexEntry]] = {}
        domain: FortranDomain = self.domain

        for fqn, obj in sorted(domain.objects.items()):
            if obj.objtype not in ("function", "subroutine"):
                continue
            if docnames and obj.docname not in docnames:
                continue

            letter = obj.dispname[0].upper()
            entries = content.setdefault(letter, [])
            # Show module context in extra column
            parts = fqn.rsplit(".", 1)
            extra = parts[0] if len(parts) > 1 else ""
            entries.append(
                IndexEntry(obj.dispname, 0, obj.docname, obj.node_id, extra, obj.objtype, "")
            )

        return sorted(content.items()), True


class FortranTypeIndex(Index):
    """Index of all Fortran derived types."""

    name = "typeindex"
    localname = "Fortran Type Index"
    shortname = "types"

    def generate(
        self, docnames: Optional[List[str]] = None
    ) -> Tuple[List[Tuple[str, List[IndexEntry]]], bool]:
        content: Dict[str, List[IndexEntry]] = {}
        domain: FortranDomain = self.domain

        for fqn, obj in sorted(domain.objects.items()):
            if obj.objtype != "type":
                continue
            if docnames and obj.docname not in docnames:
                continue

            letter = obj.dispname[0].upper()
            entries = content.setdefault(letter, [])
            parts = fqn.rsplit(".", 1)
            extra = parts[0] if len(parts) > 1 else ""
            entries.append(IndexEntry(obj.dispname, 0, obj.docname, obj.node_id, extra, "", ""))

        return sorted(content.items()), True


class ObjectEntry:
    """A documented Fortran object."""

    __slots__ = ("docname", "node_id", "objtype", "dispname")

    def __init__(self, docname: str, node_id: str, objtype: str, dispname: str):
        self.docname = docname
        self.node_id = node_id
        self.objtype = objtype
        self.dispname = dispname


class FortranDomain(Domain):
    """Fortran language domain."""

    name = "f"
    label = "Fortran"

    object_types = {
        "module": ObjType("module", "mod"),
        "submodule": ObjType("submodule", "submod"),
        "program": ObjType("program", "prog"),
        "function": ObjType("function", "func", "subr"),
        "subroutine": ObjType("subroutine", "subr", "func"),
        "type": ObjType("type", "type"),
        "variable": ObjType("variable", "var"),
        "member": ObjType("member", "mem", "var"),
        "interface": ObjType("interface", "iface"),
        "enum": ObjType("enum", "enum"),
        "boundproc": ObjType("boundproc", "bp"),
        "blockdata": ObjType("blockdata", "block"),
        "common": ObjType("common", "common"),
        "namelist": ObjType("namelist", "nml"),
    }

    directives = {
        "module": FortranModule,
        "currentmodule": FortranCurrentModule,
        "submodule": FortranSubmodule,
        "program": FortranProgram,
        "function": FortranFunction,
        "subroutine": FortranSubroutine,
        "type": FortranType,
        "variable": FortranVariable,
        "member": FortranMember,
        "interface": FortranInterface,
        "enum": FortranEnum,
        "boundproc": FortranBoundProcedure,
        "blockdata": FortranBlockData,
        "common": FortranCommon,
        "namelist": FortranNamelist,
    }

    roles = {
        "mod": FortranXRefRole(),
        "submod": FortranXRefRole(),
        "prog": FortranXRefRole(),
        "func": FortranXRefRole(),
        "subr": FortranXRefRole(),
        "type": FortranXRefRole(),
        "var": FortranXRefRole(),
        "mem": FortranXRefRole(),
        "iface": FortranXRefRole(),
        "enum": FortranXRefRole(),
        "bp": FortranXRefRole(),
        "block": FortranXRefRole(),
        "common": FortranXRefRole(),
        "nml": FortranXRefRole(),
    }

    indices = [FortranModuleIndex, FortranProcedureIndex, FortranTypeIndex]

    initial_data: Dict[str, Any] = {
        "objects": {},  # fqn -> ObjectEntry data
    }

    data_version = 1

    @property
    def objects(self) -> Dict[str, ObjectEntry]:
        data = self.data.setdefault("objects", {})
        # Reconstruct ObjectEntry from stored tuples if needed.
        # Skip objtype-qualified keys ("type:mod.name"), those are
        # auxiliary entries used only by find_obj for disambiguation.
        result = {}
        for fqn, value in data.items():
            if ":" in fqn and not fqn.startswith("f-"):
                # Objtype-qualified key: skip for public iteration
                continue
            if isinstance(value, ObjectEntry):
                result[fqn] = value
            else:
                result[fqn] = ObjectEntry(*value)
        return result

    def note_object(
        self,
        fqn: str,
        dispname: str,
        objtype: str,
        node_id: str,
        location: Any = None,
    ) -> None:
        """Record a new documented object.

        When a different objtype already occupies the same FQN (e.g. a
        type and its constructor interface share the name ``string_t``),
        the previous entry is preserved under an objtype-qualified key
        ``"prevtype:fqn"`` so that :f:type: and :f:iface: roles can
        both resolve correctly via :meth:`find_obj`.
        """
        if fqn in self.data["objects"]:
            other = self.data["objects"][fqn]
            if isinstance(other, ObjectEntry):
                other_objtype = other.objtype
                other_docname = other.docname
            else:
                other_objtype = other[2]
                other_docname = other[0]
            if other_objtype == objtype:
                # Same objtype at the same FQN: genuine duplicate
                logger.warning(
                    "duplicate Fortran object description of %s, other instance in %s",
                    fqn,
                    other_docname,
                )
            else:
                # Different objtype: preserve old entry under typed key
                typed_key = f"{other_objtype}:{fqn}"
                self.data["objects"][typed_key] = self.data["objects"][fqn]
        # Store the new entry under the plain FQN (and also under its
        # own typed key so find_obj can always find it by type).
        self.data["objects"][fqn] = ObjectEntry(self.env.docname, node_id, objtype, dispname)
        typed_key_new = f"{objtype}:{fqn}"
        self.data["objects"][typed_key_new] = ObjectEntry(
            self.env.docname, node_id, objtype, dispname
        )

    def clear_doc(self, docname: str) -> None:
        to_remove = [
            fqn
            for fqn, obj in self.data.get("objects", {}).items()
            if (isinstance(obj, ObjectEntry) and obj.docname == docname)
            or (isinstance(obj, tuple) and obj[0] == docname)
        ]
        for fqn in to_remove:
            del self.data["objects"][fqn]

    def merge_domaindata(self, docnames: List[str], otherdata: Dict) -> None:
        for fqn, obj in otherdata.get("objects", {}).items():
            if isinstance(obj, ObjectEntry):
                docname = obj.docname
            else:
                docname = obj[0]
            if docname in docnames:
                self.data["objects"][fqn] = obj

    # Procedure objtypes are interchangeable for lookup. Fortran treats
    # functions and subroutines as "procedures" and users should not need
    # to know which kind they are when writing cross-references.
    _PROC_TYPES = frozenset({"function", "subroutine"})

    def find_obj(
        self,
        modname: Optional[str],
        name: str,
        objtype: Optional[str],
    ) -> Optional[Tuple[str, ObjectEntry]]:
        """Find a Fortran object by name with case-insensitive lookup.

        When *objtype* is given and the plain-FQN entry has a different
        objtype, the objtype-qualified key ``"objtype:fqn"`` is tried so
        that types and interfaces sharing a name can both be resolved.

        Functions and subroutines are treated as interchangeable, a
        ``:f:func:`` role can resolve a subroutine and vice versa.
        """
        objects = self.data.setdefault("objects", {})
        search_name = name.lower()

        def _type_matches(obj_objtype: str) -> bool:
            """Check if *obj_objtype* satisfies the requested *objtype*."""
            if objtype is None:
                return True
            if obj_objtype == objtype:
                return True
            # Functions and subroutines are interchangeable
            if objtype in self._PROC_TYPES and obj_objtype in self._PROC_TYPES:
                return True
            return False

        def _try_fqn(fqn: str) -> Optional[Tuple[str, ObjectEntry]]:
            """Attempt to resolve *fqn*, consulting typed keys if needed."""
            if fqn in objects:
                val = objects[fqn]
                obj = val if isinstance(val, ObjectEntry) else ObjectEntry(*val)
                if _type_matches(obj.objtype):
                    return (fqn, obj)
            # Try objtype-qualified key
            if objtype is not None:
                typed_key = f"{objtype}:{fqn}"
                if typed_key in objects:
                    val = objects[typed_key]
                    obj = val if isinstance(val, ObjectEntry) else ObjectEntry(*val)
                    return (fqn, obj)
                # For procedure roles, also try the other procedure type
                if objtype in self._PROC_TYPES:
                    other = "subroutine" if objtype == "function" else "function"
                    typed_key = f"{other}:{fqn}"
                    if typed_key in objects:
                        val = objects[typed_key]
                        obj = val if isinstance(val, ObjectEntry) else ObjectEntry(*val)
                        return (fqn, obj)
            return None

        # Direct match
        result = _try_fqn(search_name)
        if result:
            return result

        # Qualified with module
        if modname:
            result = _try_fqn(f"{modname.lower()}.{search_name}")
            if result:
                return result

        # Search all objects for a suffix match (skip typed keys)
        for fqn, val in objects.items():
            if ":" in fqn:
                continue  # skip objtype-qualified keys
            if fqn.endswith(f".{search_name}"):
                obj = val if isinstance(val, ObjectEntry) else ObjectEntry(*val)
                if _type_matches(obj.objtype):
                    return (fqn, obj)
                # Check typed key for this fqn
                if objtype is not None:
                    typed_key = f"{objtype}:{fqn}"
                    if typed_key in objects:
                        val2 = objects[typed_key]
                        obj2 = val2 if isinstance(val2, ObjectEntry) else ObjectEntry(*val2)
                        return (fqn, obj2)
                    # For procedure roles, also try the other type
                    if objtype in self._PROC_TYPES:
                        other = "subroutine" if objtype == "function" else "function"
                        typed_key = f"{other}:{fqn}"
                        if typed_key in objects:
                            val2 = objects[typed_key]
                            obj2 = val2 if isinstance(val2, ObjectEntry) else ObjectEntry(*val2)
                            return (fqn, obj2)

        return None

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder,
        typ: str,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> Optional[Node]:
        """Resolve a cross-reference to a Fortran object."""
        modname = node.get("f:module")

        # Map role name to objtype
        role_to_objtype = {v.roles[0] if v.roles else k: k for k, v in self.object_types.items()}
        objtype = role_to_objtype.get(typ)

        result = self.find_obj(modname, target, objtype)
        if result is None:
            return None

        fqn, obj = result
        return make_refnode(builder, fromdocname, obj.docname, obj.node_id, contnode, fqn)

    def resolve_any_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> List[Tuple[str, Node]]:
        """Resolve a reference from the :any: role."""
        results = []
        modname = node.get("f:module")

        result = self.find_obj(modname, target, None)
        if result:
            fqn, obj = result
            role = (
                self.object_types[obj.objtype].roles[0]
                if self.object_types[obj.objtype].roles
                else obj.objtype
            )
            ref = make_refnode(builder, fromdocname, obj.docname, obj.node_id, contnode, fqn)
            results.append((f"f:{role}", ref))

        return results

    def get_objects(self) -> Iterator[Tuple[str, str, str, str, str, int]]:
        """Yield all objects for the inventory / intersphinx.

        Both plain and objtype-qualified keys are yielded so that a type
        and an interface sharing the same name both appear in the
        inventory.
        """
        seen = set()
        for key, val in self.data.get("objects", {}).items():
            obj = val if isinstance(val, ObjectEntry) else ObjectEntry(*val)
            # For typed keys like "type:mod.name", use the plain fqn
            if ":" in key:
                fqn = key.split(":", 1)[1]
            else:
                fqn = key
            dedup = (fqn, obj.objtype)
            if dedup in seen:
                continue
            seen.add(dedup)
            yield (fqn, obj.dispname, obj.objtype, obj.docname, obj.node_id, 1)

    def get_full_qualified_name(self, node: Element) -> Optional[str]:
        modname = node.get("f:module", "")
        target = node.get("reftarget", "")
        if modname:
            return f"{modname}.{target}".lower()
        return target.lower()
