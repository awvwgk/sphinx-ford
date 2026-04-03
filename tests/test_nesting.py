"""Tests for nested scoping and additional indices (M2)."""

import pytest


class TestNestedScoping:
    """Test that nested types produce correct FQNs."""

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_build_succeeds(self, app):
        app.build()

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_module_stored(self, app):
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod" in domain.objects

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_type_in_module(self, app):
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.container_type" in domain.objects
        assert domain.objects["outer_mod.container_type"].objtype == "type"

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_variable_in_type(self, app):
        """Variables nested inside a type get module.type.var FQN."""
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.container_type.count" in domain.objects
        assert domain.objects["outer_mod.container_type.count"].objtype == "variable"

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_boundproc_in_type(self, app):
        """Bound procedures inside a type get module.type.bp FQN."""
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.container_type.get_count" in domain.objects
        assert domain.objects["outer_mod.container_type.get_count"].objtype == "boundproc"

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_function_in_module_not_type(self, app):
        """Functions at module level (not inside type) get module.func FQN."""
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.helper" in domain.objects
        assert domain.objects["outer_mod.helper"].objtype == "function"

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_second_type_vars(self, app):
        """Variables in a second type get correct FQN (type context resets)."""
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.simple_type.value" in domain.objects

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_module_level_var(self, app):
        """Module-level variable (not inside type) gets module.var FQN."""
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.global_var" in domain.objects

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_subroutine_at_module_level(self, app):
        """Subroutine at module level after types gets module.sub FQN."""
        app.build()
        domain = app.env.get_domain("f")
        assert "outer_mod.init" in domain.objects


class TestProcedureIndex:
    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_procedure_index(self, app):
        """Procedure index contains functions and subroutines."""
        app.build()
        domain = app.env.get_domain("f")
        # FortranProcedureIndex is indices[1]
        idx = domain.indices[1](domain)
        content, _ = idx.generate()

        all_names = []
        for letter, entries in content:
            for entry in entries:
                all_names.append(entry.name)

        assert "helper" in all_names
        assert "init" in all_names

    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_procedure_index_extra(self, app):
        """Procedure index shows module name in extra column."""
        app.build()
        domain = app.env.get_domain("f")
        idx = domain.indices[1](domain)
        content, _ = idx.generate()

        for letter, entries in content:
            for entry in entries:
                if entry.name == "helper":
                    assert entry.extra == "outer_mod"


class TestTypeIndex:
    @pytest.mark.sphinx("dummy", testroot="nesting")
    def test_type_index(self, app):
        """Type index contains derived types."""
        app.build()
        domain = app.env.get_domain("f")
        # FortranTypeIndex is indices[2]
        idx = domain.indices[2](domain)
        content, _ = idx.generate()

        all_names = []
        for letter, entries in content:
            for entry in entries:
                all_names.append(entry.name)

        assert "container_type" in all_names
        assert "simple_type" in all_names
