"""Tests for the Fortran domain registration and basic operation."""

import pytest

from sphinx_ford.domain import FortranDomain


class TestDomainRegistration:
    """Test that the domain registers correctly."""

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_domain_registered(self, app):
        """Domain 'f' is registered after setup."""
        app.build()
        assert "f" in app.env.domains
        domain = app.env.get_domain("f")
        assert isinstance(domain, FortranDomain)
        assert domain.name == "f"
        assert domain.label == "Fortran"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_object_types(self, app):
        """All expected object types are registered."""
        app.build()
        domain = app.env.get_domain("f")
        expected = {
            "module",
            "submodule",
            "program",
            "function",
            "subroutine",
            "type",
            "variable",
            "member",
            "interface",
            "enum",
            "boundproc",
            "blockdata",
            "common",
            "namelist",
        }
        assert set(domain.object_types.keys()) == expected

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_roles_registered(self, app):
        """All expected roles are registered."""
        app.build()
        domain = app.env.get_domain("f")
        expected = {
            "mod",
            "submod",
            "prog",
            "func",
            "subr",
            "type",
            "var",
            "mem",
            "iface",
            "enum",
            "bp",
            "block",
            "common",
            "nml",
        }
        assert set(domain.roles.keys()) == expected

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_directives_registered(self, app):
        """All expected directives are registered."""
        app.build()
        domain = app.env.get_domain("f")
        expected = {
            "module",
            "currentmodule",
            "submodule",
            "program",
            "function",
            "subroutine",
            "type",
            "variable",
            "member",
            "interface",
            "enum",
            "boundproc",
            "blockdata",
            "common",
            "namelist",
        }
        assert set(domain.directives.keys()) == expected


class TestDomainData:
    """Test domain data storage and retrieval."""

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_objects_populated(self, app):
        """Objects are populated after building."""
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        # Should have modules
        assert "test_mod" in objects
        assert objects["test_mod"].objtype == "module"

        assert "another_mod" in objects
        assert objects["another_mod"].objtype == "module"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_function_in_module(self, app):
        """Functions within modules get qualified names."""
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        assert "test_mod.test_func" in objects
        assert objects["test_mod.test_func"].objtype == "function"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_subroutine_in_module(self, app):
        """Subroutines within modules get qualified names."""
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        assert "test_mod.test_sub" in objects
        assert objects["test_mod.test_sub"].objtype == "subroutine"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_type_in_module(self, app):
        """Types within modules get qualified names."""
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        assert "test_mod.test_type" in objects
        assert objects["test_mod.test_type"].objtype == "type"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_variable_in_module(self, app):
        """Variables within modules get qualified names."""
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        assert "test_mod.module_var" in objects
        assert objects["test_mod.module_var"].objtype == "variable"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_interface_in_module(self, app):
        """Interfaces within modules get qualified names."""
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        assert "test_mod.test_iface" in objects
        assert objects["test_mod.test_iface"].objtype == "interface"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_get_objects(self, app):
        """get_objects() yields all documented entities."""
        app.build()
        domain = app.env.get_domain("f")
        obj_list = list(domain.get_objects())

        # Should have at least: test_mod, another_mod, test_func, test_sub,
        # test_type, value, get_value, test_iface, module_var
        assert len(obj_list) >= 9

        # Each entry is (fqn, dispname, objtype, docname, node_id, priority)
        for entry in obj_list:
            assert len(entry) == 6

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_case_insensitive_storage(self, app):
        """All names are stored lowercase."""
        app.build()
        domain = app.env.get_domain("f")
        for fqn in domain.objects:
            assert fqn == fqn.lower(), f"FQN '{fqn}' is not lowercase"

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_clear_doc(self, app):
        """clear_doc() removes objects from a specific document."""
        app.build()
        domain = app.env.get_domain("f")
        assert len(domain.objects) > 0

        domain.clear_doc("index")
        assert len(domain.data["objects"]) == 0


class TestCrossReferences:
    """Test cross-reference resolution."""

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_build_succeeds(self, app):
        """Build completes without errors."""
        app.build()
        # No exceptions means success

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_find_module(self, app):
        """find_obj locates a module."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "mymod", "module")
        assert result is not None
        fqn, obj = result
        assert fqn == "mymod"
        assert obj.objtype == "module"

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_find_function_unqualified(self, app):
        """find_obj locates a function by unqualified name."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "myfunc", "function")
        assert result is not None
        fqn, obj = result
        assert obj.objtype == "function"

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_find_function_qualified(self, app):
        """find_obj locates a function by qualified name."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "mymod.myfunc", "function")
        assert result is not None

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_find_case_insensitive(self, app):
        """find_obj is case-insensitive."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "MYFUNC", "function")
        assert result is not None
        fqn, obj = result
        assert obj.objtype == "function"

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_find_with_module_context(self, app):
        """find_obj searches within module context."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj("mymod", "myfunc", "function")
        assert result is not None

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_find_nonexistent(self, app):
        """find_obj returns None for nonexistent objects."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "nonexistent", "function")
        assert result is None

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_func_finds_subroutine(self, app):
        """find_obj with objtype='function' also matches subroutines."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "mysub", "function")
        assert result is not None
        fqn, obj = result
        assert obj.objtype == "subroutine"

    @pytest.mark.sphinx("dummy", testroot="xref")
    def test_subr_finds_function(self, app):
        """find_obj with objtype='subroutine' also matches functions."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj(None, "myfunc", "subroutine")
        assert result is not None
        fqn, obj = result
        assert obj.objtype == "function"


class TestSignatureParsing:
    """Test signature edge cases."""

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_variable_default_with_parens(self, app):
        """Default values containing parentheses are preserved correctly."""
        app.build()
        domain = app.env.get_domain("f")
        result = domain.find_obj("test_mod", "FMT_INT", "variable")
        assert result is not None
        fqn, obj = result
        assert obj.objtype == "variable"
        # Name should be FMT_INT, not truncated at the paren
        assert fqn == "test_mod.fmt_int"


class TestModuleIndex:
    """Test the module index."""

    @pytest.mark.sphinx("dummy", testroot="module")
    def test_index_entries(self, app):
        """Module index contains documented modules."""
        app.build()
        domain = app.env.get_domain("f")
        index = domain.indices[0]
        idx_instance = index(domain)
        content, collapse = idx_instance.generate()

        # Should have entries
        assert len(content) > 0

        # Collect all module names from the index
        all_names = []
        for letter, entries in content:
            for entry in entries:
                all_names.append(entry.name)

        assert "test_mod" in all_names
        assert "another_mod" in all_names
