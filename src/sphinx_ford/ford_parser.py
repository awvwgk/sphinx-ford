"""FORD JSON parser: import modules.json from FORD output.

Reads FORD's ``modules.json`` (produced by ``ford --externalize``) and
creates domain objects for cross-project linking.  Also provides
utilities to generate ``objects.inv`` from FORD data and to export
sphinx-ford domain objects as FORD-compatible ``modules.json``.
"""

from __future__ import annotations

import json
import logging
import zlib
from pathlib import Path
from typing import Any
from urllib.parse import quote as url_quote

logger = logging.getLogger(__name__)


# FORD URL patterns  (relative to the FORD site root)
_FORD_URL_PATTERNS = {
    "module": "module/{name}.html",
    "function": "proc/{name}.html",
    "subroutine": "proc/{name}.html",
    "interface": "interface/{name}.html",
    "type": "type/{name}.html",
    "program": "program/{name}.html",
    "variable": "type/{parent}.html#variable-{name}",
    "boundprocedure": "type/{parent}.html#boundproc-{name}",
}


def _obj_type_from_ford(ford_obj: str, proctype: str | None = None) -> str:
    """Map FORD's 'obj' / 'proctype' to sphinx-ford objtype."""
    if proctype:
        pt = proctype.lower()
        if pt in ("function", "subroutine"):
            return pt
    obj = ford_obj.lower()
    mapping = {
        "module": "module",
        "proc": "function",  # fallback
        "function": "function",
        "subroutine": "subroutine",
        "type": "type",
        "interface": "interface",
        "variable": "variable",
        "boundprocedure": "boundproc",
        "program": "program",
    }
    return mapping.get(obj, obj)


def parse_modules_json(
    data: list[dict],
    base_url: str = "",
) -> list[dict]:
    """Parse FORD ``modules.json`` into a flat list of entity dicts.

    Each returned dict has keys: ``name``, ``fqn``, ``objtype``,
    ``url``, ``dispname``.

    Parameters
    ----------
    data
        The parsed JSON (list of module dicts).
    base_url
        Base URL to prepend to relative FORD URLs.

    Returns
    -------
    list[dict]
        Flat list of entity records suitable for domain registration.
    """
    entities: list[dict] = []
    base = base_url.rstrip("/")

    for mod_dict in data:
        mod_name = mod_dict.get("name", "")
        if not mod_name:
            continue

        mod_url_pattern = _FORD_URL_PATTERNS.get("module", "")
        mod_url = f"{base}/{mod_url_pattern.format(name=url_quote(mod_name))}"

        entities.append(
            {
                "name": mod_name,
                "fqn": mod_name.lower(),
                "objtype": "module",
                "url": mod_url,
                "dispname": mod_name,
            }
        )

        # Nested entities within the module
        for key, objtype in [
            ("functions", "function"),
            ("subroutines", "subroutine"),
            ("interfaces", "interface"),
            ("types", "type"),
            ("variables", "variable"),
            ("boundprocs", "boundproc"),
        ]:
            for item in mod_dict.get(key, []) or []:
                if not item or not isinstance(item, dict):
                    continue
                item_name = item.get("name", "")
                if not item_name:
                    continue

                # Determine objtype from FORD data
                ford_obj = item.get("obj", objtype)
                ford_proctype = item.get("proctype")
                actual_objtype = _obj_type_from_ford(ford_obj, ford_proctype)

                # Build URL
                url_pattern = _FORD_URL_PATTERNS.get(
                    ford_proctype.lower() if ford_proctype else ford_obj.lower(),
                    _FORD_URL_PATTERNS.get(objtype, ""),
                )
                url = f"{base}/{url_pattern.format(name=url_quote(item_name), parent=url_quote(mod_name))}"

                fqn = f"{mod_name.lower()}.{item_name.lower()}"

                entities.append(
                    {
                        "name": item_name,
                        "fqn": fqn,
                        "objtype": actual_objtype,
                        "url": url,
                        "dispname": item_name,
                    }
                )

    return entities


def load_modules_json(path: str | Path) -> list[dict]:
    """Load and parse a FORD ``modules.json`` file.

    Parameters
    ----------
    path
        Path to the ``modules.json`` file.

    Returns
    -------
    list[dict]
        Raw JSON data (list of module dicts).
    """
    p = Path(path)
    if not p.exists():
        logger.warning("sphinx-ford: modules.json not found: %s", p)
        return []

    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("sphinx-ford: failed to read modules.json: %s", e)
        return []

    if not isinstance(data, list):
        logger.warning("sphinx-ford: modules.json is not a list")
        return []

    return data


def _inv_header(project_name: str = "FORD Project", version: str = "") -> bytes:
    """Create the Sphinx objects.inv header."""
    lines = [
        b"# Sphinx inventory version 2",
        f"# Project: {project_name}".encode(),
        f"# Version: {version}".encode(),
        b"# The remainder of this file is compressed using zlib.",
    ]
    return b"\n".join(lines) + b"\n"


def _inv_entry(name: str, domaintype: str, priority: int, url: str, dispname: str) -> bytes:
    """Create a single objects.inv entry line."""
    if dispname == name:
        dispname = "-"
    return f"{name} {domaintype} {priority} {url} {dispname}\n".encode()


# Map sphinx-ford objtype to the role used in objects.inv
_OBJTYPE_TO_ROLE = {
    "module": "f:mod",
    "function": "f:func",
    "subroutine": "f:subr",
    "type": "f:type",
    "variable": "f:var",
    "member": "f:mem",
    "interface": "f:iface",
    "program": "f:prog",
    "boundproc": "f:bp",
    "enum": "f:enum",
    "submodule": "f:submod",
    "blockdata": "f:block",
    "common": "f:common",
    "namelist": "f:nml",
}


def generate_objects_inv(
    entities: list[dict],
    project_name: str = "FORD Project",
    version: str = "",
) -> bytes:
    """Generate a Sphinx-compatible ``objects.inv`` from entity dicts.

    Parameters
    ----------
    entities
        List of entity dicts from :func:`parse_modules_json`.
    project_name
        Project name for the inventory header.
    version
        Project version for the inventory header.

    Returns
    -------
    bytes
        Complete ``objects.inv`` file content.
    """
    header = _inv_header(project_name, version)

    body_lines: list[bytes] = []
    for ent in entities:
        domaintype = _OBJTYPE_TO_ROLE.get(ent["objtype"], f"f:{ent['objtype']}")
        url = ent["url"]
        body_lines.append(_inv_entry(ent["fqn"], domaintype, 1, url, ent["dispname"]))

    compressed = zlib.compress(b"".join(body_lines))
    return header + compressed


def write_objects_inv(
    entities: list[dict],
    output_path: str | Path,
    project_name: str = "FORD Project",
    version: str = "",
) -> None:
    """Write an ``objects.inv`` file from entity dicts."""
    data = generate_objects_inv(entities, project_name, version)
    Path(output_path).write_bytes(data)
    logger.info("sphinx-ford: wrote %s (%d entries)", output_path, len(entities))


def domain_to_ford_json(
    domain: Any,
    builder: Any = None,
) -> list[dict]:
    """Export sphinx-ford domain objects as FORD-compatible modules.json.

    Parameters
    ----------
    domain
        The FortranDomain instance.
    builder
        Sphinx builder (used to resolve URIs). If None, URLs are omitted.

    Returns
    -------
    list[dict]
        FORD-format modules list.
    """
    objects = domain.objects
    modules: dict[str, dict] = {}

    # Group entities by module
    for fqn, obj in objects.items():
        if obj.objtype == "module":
            modules[fqn] = {
                "name": obj.dispname,
                "obj": "module",
                "external_url": "",
                "functions": [],
                "subroutines": [],
                "interfaces": [],
                "types": [],
                "variables": [],
                "boundprocs": [],
                "pub_procs": {},
                "pub_types": {},
                "pub_vars": {},
            }

    # Fill module contents
    for fqn, obj in objects.items():
        if obj.objtype == "module":
            continue

        # Find parent module
        parts = fqn.split(".")
        if len(parts) < 2:
            continue
        mod_fqn = parts[0]
        if mod_fqn not in modules:
            continue

        mod = modules[mod_fqn]
        entity_name = obj.dispname

        # Resolve URL if builder available
        url = ""
        if builder:
            try:
                uri = builder.get_target_uri(obj.docname)
                url = f"{uri}#{obj.node_id}"
            except Exception:
                pass

        entry = {
            "name": entity_name,
            "obj": obj.objtype,
            "external_url": url,
        }

        if obj.objtype == "function":
            entry["proctype"] = "Function"
            mod["functions"].append(entry)
            mod["pub_procs"][entity_name] = entry
        elif obj.objtype == "subroutine":
            entry["proctype"] = "Subroutine"
            mod["subroutines"].append(entry)
            mod["pub_procs"][entity_name] = entry
        elif obj.objtype == "interface":
            mod["interfaces"].append(entry)
            mod["pub_procs"][entity_name] = entry
        elif obj.objtype == "type":
            mod["types"].append(entry)
            mod["pub_types"][entity_name] = entry
        elif obj.objtype == "variable":
            mod["variables"].append(entry)
            mod["pub_vars"][entity_name] = entry
        elif obj.objtype == "member":
            mod["variables"].append(entry)
            mod["pub_vars"][entity_name] = entry
        elif obj.objtype == "boundproc":
            mod["boundprocs"].append(entry)

    # Set module URLs
    for mod_fqn, mod in modules.items():
        if builder and mod_fqn in objects:
            obj = objects[mod_fqn]
            try:
                uri = builder.get_target_uri(obj.docname)
                mod["external_url"] = f"{uri}#{obj.node_id}"
            except Exception:
                pass

    return list(modules.values())


def write_ford_modules_json(
    domain: Any,
    output_path: str | Path,
    builder: Any = None,
) -> None:
    """Write FORD-compatible ``modules.json`` from the domain."""
    data = domain_to_ford_json(domain, builder)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info("sphinx-ford: wrote %s (%d modules)", p, len(data))
