"""Tests for FORD JSON parser, objects.inv generation, and reverse export (M4)."""

import json
import zlib
from pathlib import Path

import pytest

from sphinx_ford.ford_parser import (
    domain_to_ford_json,
    generate_objects_inv,
    load_modules_json,
    parse_modules_json,
    write_ford_modules_json,
    write_objects_inv,
)

# -- Sample FORD modules.json data ----------------------------------------

SAMPLE_MODULES_JSON = [
    {
        "name": "mymod",
        "obj": "module",
        "external_url": "module/mymod.html",
        "permission": "public",
        "functions": [
            {
                "name": "myfunc",
                "obj": "proc",
                "proctype": "Function",
                "external_url": "proc/myfunc.html",
            },
        ],
        "subroutines": [
            {
                "name": "mysub",
                "obj": "proc",
                "proctype": "Subroutine",
                "external_url": "proc/mysub.html",
            },
        ],
        "types": [
            {
                "name": "mytype",
                "obj": "type",
                "external_url": "type/mytype.html",
            },
        ],
        "interfaces": [
            {
                "name": "myiface",
                "obj": "interface",
                "external_url": "interface/myiface.html",
            },
        ],
        "variables": [
            {
                "name": "myvar",
                "obj": "variable",
                "external_url": "",
            },
        ],
    },
    {
        "name": "othermod",
        "obj": "module",
        "external_url": "module/othermod.html",
        "functions": [],
        "subroutines": [],
        "types": [],
        "interfaces": [],
        "variables": [],
    },
]


class TestParseModulesJson:
    def test_parse_basic(self):
        entities = parse_modules_json(SAMPLE_MODULES_JSON, "https://example.com")
        names = {e["fqn"] for e in entities}
        assert "mymod" in names
        assert "othermod" in names
        assert "mymod.myfunc" in names
        assert "mymod.mysub" in names
        assert "mymod.mytype" in names
        assert "mymod.myiface" in names
        assert "mymod.myvar" in names

    def test_parse_objtypes(self):
        entities = parse_modules_json(SAMPLE_MODULES_JSON)
        by_fqn = {e["fqn"]: e for e in entities}
        assert by_fqn["mymod"]["objtype"] == "module"
        assert by_fqn["mymod.myfunc"]["objtype"] == "function"
        assert by_fqn["mymod.mysub"]["objtype"] == "subroutine"
        assert by_fqn["mymod.mytype"]["objtype"] == "type"
        assert by_fqn["mymod.myiface"]["objtype"] == "interface"
        assert by_fqn["mymod.myvar"]["objtype"] == "variable"

    def test_parse_urls(self):
        entities = parse_modules_json(SAMPLE_MODULES_JSON, "https://example.com")
        by_fqn = {e["fqn"]: e for e in entities}
        assert "module/mymod.html" in by_fqn["mymod"]["url"]
        assert "proc/myfunc.html" in by_fqn["mymod.myfunc"]["url"]
        assert "type/mytype.html" in by_fqn["mymod.mytype"]["url"]

    def test_parse_empty(self):
        entities = parse_modules_json([])
        assert entities == []

    def test_parse_no_name(self):
        entities = parse_modules_json([{"obj": "module"}])
        assert entities == []

    def test_parse_null_entries(self):
        """Handle None entries in entity lists (FORD sometimes produces these)."""
        data = [
            {
                "name": "mod",
                "functions": [None, {"name": "f", "obj": "proc", "proctype": "Function"}],
            }
        ]
        entities = parse_modules_json(data)
        assert len(entities) == 2  # module + function


class TestLoadModulesJson:
    def test_load_valid(self, tmp_path):
        p = tmp_path / "modules.json"
        p.write_text(json.dumps(SAMPLE_MODULES_JSON))
        data = load_modules_json(p)
        assert len(data) == 2
        assert data[0]["name"] == "mymod"

    def test_load_nonexistent(self, tmp_path):
        data = load_modules_json(tmp_path / "nope.json")
        assert data == []

    def test_load_invalid_json(self, tmp_path):
        p = tmp_path / "modules.json"
        p.write_text("not json!")
        data = load_modules_json(p)
        assert data == []

    def test_load_not_list(self, tmp_path):
        p = tmp_path / "modules.json"
        p.write_text('{"not": "a list"}')
        data = load_modules_json(p)
        assert data == []


class TestGenerateObjectsInv:
    def test_generate(self):
        entities = parse_modules_json(SAMPLE_MODULES_JSON, "https://example.com")
        inv_data = generate_objects_inv(entities, "TestProject", "1.0")

        # Should start with Sphinx inventory header
        assert inv_data.startswith(b"# Sphinx inventory version 2\n")
        assert b"# Project: TestProject" in inv_data
        assert b"# Version: 1.0" in inv_data

        # Decompress the body
        header_end = inv_data.index(b"# The remainder of this file")
        header_end = inv_data.index(b"\n", header_end) + 1
        compressed = inv_data[header_end:]
        body = zlib.decompress(compressed).decode()

        # Should contain entries
        assert "mymod f:mod" in body
        assert "mymod.myfunc f:func" in body
        assert "mymod.mysub f:subr" in body
        assert "mymod.mytype f:type" in body

    def test_write(self, tmp_path):
        entities = parse_modules_json(SAMPLE_MODULES_JSON)
        output = tmp_path / "objects.inv"
        write_objects_inv(entities, output, "Test", "0.1")
        assert output.exists()
        assert output.stat().st_size > 0


class TestDomainToFordJson:
    @pytest.mark.sphinx("dummy", testroot="module")
    def test_export(self, app):
        app.build()
        domain = app.env.get_domain("f")
        data = domain_to_ford_json(domain)

        # Should have modules
        assert len(data) > 0
        mod_names = [m["name"] for m in data]
        assert "test_mod" in mod_names
        assert "another_mod" in mod_names

        # test_mod should have contents
        test_mod = next(m for m in data if m["name"] == "test_mod")
        assert len(test_mod["functions"]) > 0
        assert len(test_mod["subroutines"]) > 0
        assert len(test_mod["types"]) > 0

        func_names = [f["name"] for f in test_mod["functions"]]
        assert "test_func" in func_names

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_write_modules_json(self, app, tmp_path):
        app.build()
        domain = app.env.get_domain("f")
        output = tmp_path / "modules.json"
        write_ford_modules_json(domain, output)

        assert output.exists()
        data = json.loads(output.read_text())
        assert isinstance(data, list)
        assert len(data) > 0


class TestExportOnBuild:
    @pytest.mark.sphinx(
        "html",
        testroot="module",
        confoverrides={"ford_export_modules_json": True},
        freshenv=True,
    )
    def test_modules_json_exported(self, app):
        """When ford_export_modules_json is True, modules.json appears in output."""
        app.build()
        output = Path(app.outdir) / "modules.json"
        assert output.exists()
        data = json.loads(output.read_text())
        assert isinstance(data, list)
        mod_names = [m["name"] for m in data]
        assert "test_mod" in mod_names

    @pytest.mark.sphinx(
        "html",
        testroot="html",
        freshenv=True,
    )
    def test_no_export_by_default(self, app):
        """By default, modules.json is NOT exported."""
        app.build()
        output = Path(app.outdir) / "modules.json"
        assert not output.exists()
