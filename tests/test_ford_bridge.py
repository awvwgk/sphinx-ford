"""Tests for the FORD bridge (M3)."""

import pytest

ford = pytest.importorskip("ford")


class TestFordBridgeLoading:
    """Test FORD project loading."""

    def test_load_toml_f(self, toml_f_ford_file):
        """Load toml-f project via FORD API."""
        from sphinx_ford.ford_bridge import _load_ford_project

        project = _load_ford_project(str(toml_f_ford_file))
        assert len(project.modules) > 0
        assert len(project.files) > 0

        # Check known modules exist
        mod_names = [m.name.lower() for m in project.modules]
        assert "tomlf" in mod_names

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file raises ExtensionError."""
        from sphinx.errors import ExtensionError

        from sphinx_ford.ford_bridge import _load_ford_project

        with pytest.raises(ExtensionError, match="not found"):
            _load_ford_project("/nonexistent/project.md")

    def test_variable_substitution(self):
        """@VAR@ substitution works."""
        from sphinx_ford.ford_bridge import _substitute_vars

        text = "src_dir: @CMAKE_SOURCE_DIR@/src"
        result = _substitute_vars(text, {"CMAKE_SOURCE_DIR": "/path/to/project"})
        assert result == "src_dir: /path/to/project/src"


class TestPreprocessorDetection:
    """Test preprocessor availability detection."""

    def test_check_preprocessor_available(self):
        """Available preprocessor passes validation."""
        from sphinx_ford._ford_compat import _check_preprocessor

        # python is definitely available
        _check_preprocessor(
            {"fpp_extensions": ["F90"], "preprocessor": "python", "preprocess": True},
            preprocess=True,
        )
        # Should not raise

    def test_check_preprocessor_disabled(self):
        """Disabled preprocessing skips validation."""
        from sphinx_ford._ford_compat import _check_preprocessor

        # Even a nonexistent preprocessor should pass when disabled
        _check_preprocessor(
            {"fpp_extensions": ["F90"], "preprocessor": "nonexistent_pp_xyz", "preprocess": True},
            preprocess=False,
        )

    def test_check_preprocessor_no_fpp_extensions(self):
        """No fpp_extensions means no preprocessing needed."""
        from sphinx_ford._ford_compat import _check_preprocessor

        _check_preprocessor(
            {"fpp_extensions": [], "preprocessor": "nonexistent_pp_xyz", "preprocess": True},
            preprocess=True,
        )

    def test_check_preprocessor_missing(self):
        """Missing preprocessor raises ExtensionError."""
        from sphinx.errors import ExtensionError

        from sphinx_ford._ford_compat import _check_preprocessor

        with pytest.raises(ExtensionError, match="not found"):
            _check_preprocessor(
                {
                    "fpp_extensions": ["F90"],
                    "preprocessor": "nonexistent_pp_xyz_12345",
                    "preprocess": True,
                },
                preprocess=True,
            )

    def test_check_preprocessor_error_message(self):
        """Error message includes helpful instructions."""
        from sphinx.errors import ExtensionError

        from sphinx_ford._ford_compat import _check_preprocessor

        with pytest.raises(ExtensionError, match="ford_preprocess = False"):
            _check_preprocessor(
                {
                    "fpp_extensions": ["fypp"],
                    "preprocessor": "totally_fake_command",
                    "preprocess": True,
                },
                preprocess=True,
            )


class TestModuleToRst:
    """Test FORD module to RST conversion."""

    def test_module_rst_generation(self, toml_f_ford_file):
        """Generate RST from a FORD module."""
        from sphinx_ford.ford_bridge import _load_ford_project, _module_to_rst

        project = _load_ford_project(str(toml_f_ford_file))

        # Find a module with content
        target_mod = None
        for mod in project.modules:
            if mod.functions or mod.subroutines or mod.types:
                target_mod = mod
                break

        assert target_mod is not None, "No module with content found"

        rst_lines = _module_to_rst(target_mod)
        rst_text = "\n".join(rst_lines)

        # Should contain module directive
        assert f".. f:module:: {target_mod.name}" in rst_text

        # Should contain function/subroutine directives
        # Some may be nested under interfaces instead of at module level
        for func in target_mod.functions:
            assert any(
                line.strip().startswith(".. f:function::") and func.name in line
                for line in rst_lines
            ), f"Function directive for {func.name} missing"
        for sub in target_mod.subroutines:
            assert any(
                line.strip().startswith(".. f:subroutine::") and sub.name in line
                for line in rst_lines
            ), f"Subroutine directive for {sub.name} missing"

    def test_interface_includes_modprocs(self, toml_f_ford_file):
        """Generic interfaces should include their member procedures."""
        from sphinx_ford.ford_bridge import _load_ford_project, _module_to_rst

        project = _load_ford_project(str(toml_f_ford_file))

        # Find module with generic interfaces that have modprocs
        for mod in project.modules:
            ifaces = getattr(mod, "interfaces", [])
            for iface in ifaces:
                modprocs = getattr(iface, "modprocs", []) or []
                if modprocs and getattr(iface, "generic", False):
                    rst_lines = _module_to_rst(mod)
                    rst_text = "\n".join(rst_lines)
                    type_names = {t.name.lower() for t in getattr(mod, "types", [])}
                    is_constructor_iface = iface.name.lower() in type_names

                    # Non-constructor interfaces render as interface directives.
                    # Constructor interfaces (same name as a type) are rendered
                    # under the type's "Constructors" section.
                    if not is_constructor_iface:
                        assert f".. f:interface:: {iface.name}" in rst_text
                    else:
                        assert "**Constructors:**" in rst_text

                    # Each modproc should appear as nested func/sub
                    for mp in modprocs:
                        mp_name = getattr(mp, "name", None)
                        if mp_name:
                            assert mp_name in rst_text, (
                                f"modproc {mp_name} missing from {iface.name}"
                            )

                    # Modproc procedures should NOT appear at module level
                    # (indented 3 spaces = module level, 6+ = nested)
                    for mp in modprocs:
                        mp_name = getattr(mp, "name", None)
                        if mp_name:
                            for line in rst_lines:
                                if f":: {mp_name}(" in line or f":: {mp_name}" in line:
                                    assert line.startswith("      "), (
                                        f"{mp_name} at wrong indent: {line!r}"
                                    )
                    return  # Found a good test case

        pytest.skip("No module with generic interfaces found")

    def test_module_with_types(self, toml_f_ford_file):
        """Generate RST for a module containing types."""
        from sphinx_ford.ford_bridge import _load_ford_project, _module_to_rst

        project = _load_ford_project(str(toml_f_ford_file))

        # Find module with types
        for mod in project.modules:
            if mod.types:
                rst_lines = _module_to_rst(mod)
                rst_text = "\n".join(rst_lines)
                for t in mod.types:
                    assert f".. f:type:: {t.name}" in rst_text
                break

    def test_abstract_type_option_emitted(self):
        """Abstract FORD types emit :abstract: for f:type directives."""
        from sphinx_ford.ford_bridge import _ford_entity_to_rst

        class MockType:
            name = "abstract_lexer"
            permission = None
            extends = "toml_lexer"
            abstract = True
            doc = None

        rst_lines = _ford_entity_to_rst(MockType(), "type", module_name="tomlf")
        rst_text = "\n".join(rst_lines)

        assert ".. f:type:: abstract_lexer" in rst_text
        assert "   :extends: toml_lexer" in rst_text
        assert "   :abstract:" in rst_text

    def test_boundproc_binding_links(self, toml_f_ford_file):
        """Bound procedures have cross-reference links to their implementations."""
        from sphinx_ford.ford_bridge import _load_ford_project, _module_to_rst

        project = _load_ford_project(str(toml_f_ford_file))

        # Find a module with a type that has bound procedures
        for mod in project.modules:
            for typ in getattr(mod, "types", []):
                boundprocs = getattr(typ, "boundprocs", [])
                if not boundprocs:
                    continue
                # Check there are matching module-level procs
                mod_funcs = {f.name.lower() for f in getattr(mod, "functions", [])}
                mod_subs = {s.name.lower() for s in getattr(mod, "subroutines", [])}
                mod_procs = mod_funcs | mod_subs
                matchable = [
                    bp
                    for bp in boundprocs
                    if any(b.lower() in mod_procs for b in getattr(bp, "bindings", []) or [])
                ]
                if not matchable:
                    continue

                rst_lines = _module_to_rst(mod, visibility=None)
                rst_text = "\n".join(rst_lines)

                for bp in matchable:
                    bindings = getattr(bp, "bindings", []) or []
                    for bname in bindings:
                        if bname.lower() in mod_funcs or bname.lower() in mod_subs:
                            assert f":f:func:`{bname} <{mod.name}.{bname}>`" in rst_text
                return  # Found a valid test case

        pytest.skip("No module with bound procedures found")

    def test_boundproc_expands_hidden_procs(self, toml_f_ford_file):
        """Bound procedures inline-expand hidden procedure docs."""
        from sphinx_ford.ford_bridge import _load_ford_project, _module_to_rst

        project = _load_ford_project(str(toml_f_ford_file))

        # Find a module where bound procs bind to private procedures
        for mod in project.modules:
            for typ in getattr(mod, "types", []):
                boundprocs = getattr(typ, "boundprocs", [])
                if not boundprocs:
                    continue
                mod_funcs = {f.name.lower(): f for f in getattr(mod, "functions", [])}
                mod_subs = {s.name.lower(): s for s in getattr(mod, "subroutines", [])}
                # Find a bound proc that binds to a private procedure
                for bp in boundprocs:
                    bindings = getattr(bp, "bindings", []) or []
                    for bname in bindings:
                        proc = mod_funcs.get(bname.lower()) or mod_subs.get(bname.lower())
                        if proc and getattr(proc, "permission", "public") == "private":
                            # Generate with visibility that excludes private
                            rst_lines = _module_to_rst(mod, visibility={"public", "protected"})
                            rst_text = "\n".join(rst_lines)

                            # Should NOT have a "Binds to" link for this proc
                            assert f":f:func:`{bname} <{mod.name}.{bname}>`" not in rst_text

                            # Should have inline-expanded arguments
                            proc_args = getattr(proc, "args", [])
                            if proc_args:
                                assert "**Arguments:**" in rst_text

                            return  # Found a valid test case

        pytest.skip("No module with private bound procedure targets found")

    def test_uses_dedup_and_missing_module_fallback(self):
        """Uses entries deduplicate names and avoid xrefs for missing modules."""
        from sphinx_ford.ford_bridge import _module_to_rst

        class MockModule:
            name = "mock_mod"
            permission = None
            doc = None
            uses = [
                "present_mod",
                "present_mod",
                "missing_mod",
            ]
            variables = []
            interfaces = []
            types = []
            functions = []
            subroutines = []

        rst_text = "\n".join(_module_to_rst(MockModule(), available_module_names={"present_mod"}))

        assert rst_text.count(":f:mod:`present_mod`") == 1
        assert "missing_mod" in rst_text
        assert ":f:mod:`missing_mod`" not in rst_text


class TestCaseNormalization:
    """Test ford_case normalization."""

    def test_normalize_case_none(self):
        """With ford_case=None, text is preserved as-is."""
        import sphinx_ford.ford_bridge as fb

        fb._ford_case = None
        assert fb._normalize_case("POINTER") == "POINTER"
        assert fb._normalize_case("type") == "type"

    def test_normalize_case_lower(self):
        """With ford_case='lower', text is lowered."""
        import sphinx_ford.ford_bridge as fb

        fb._ford_case = "lower"
        assert fb._normalize_case("POINTER") == "pointer"
        assert fb._normalize_case("DIMENSION(:)") == "dimension(:)"
        fb._ford_case = None

    def test_normalize_case_upper(self):
        """With ford_case='upper', text is uppered."""
        import sphinx_ford.ford_bridge as fb

        fb._ford_case = "upper"
        assert fb._normalize_case("pointer") == "POINTER"
        assert fb._normalize_case("dimension(:)") == "DIMENSION(:)"
        fb._ford_case = None

    def test_format_type_decl_lowered(self):
        """_format_type_decl respects ford_case='lower'."""
        import sphinx_ford.ford_bridge as fb

        fb._ford_case = "lower"

        class MockVar:
            vartype = "type"
            proto = ["some_type"]
            kind = None
            strlen = None
            attribs = ["POINTER", "CONTIGUOUS"]

        result = fb._format_type_decl(MockVar())
        assert "pointer" in result
        assert "contiguous" in result
        assert "POINTER" not in result
        fb._ford_case = None

    def test_format_param_qualifier_lowered(self):
        """_format_param_qualifier respects ford_case='lower'."""
        import sphinx_ford.ford_bridge as fb

        fb._ford_case = "lower"

        class MockArg:
            vartype = "type"
            proto = ["some_type"]
            kind = None
            strlen = None
            intent = "in"
            optional = True
            attribs = ["POINTER"]

        result = fb._format_param_qualifier(MockArg())
        assert "*pointer*" in result
        assert "*intent(in)*" in result
        assert "*optional*" in result
        assert "POINTER" not in result
        fb._ford_case = None

    def test_format_param_qualifier_uppered(self):
        """_format_param_qualifier respects ford_case='upper'."""
        import sphinx_ford.ford_bridge as fb

        fb._ford_case = "upper"

        class MockArg:
            vartype = "integer"
            proto = None
            kind = None
            strlen = None
            intent = "in"
            optional = False
            attribs = ["pointer"]

        result = fb._format_param_qualifier(MockArg())
        assert "*INTEGER*" in result
        assert "*INTENT(IN)*" in result
        assert "*POINTER*" in result
        fb._ford_case = None


class TestFordBridgeIntegration:
    """Test FORD bridge with Sphinx build."""

    def test_automodule_build(self, toml_f_ford_file, rootdir, tmp_path):
        """Build with f:automodule directive."""
        import shutil

        from sphinx.application import Sphinx

        # Copy the test root to a temp dir
        srcdir = tmp_path / "src"
        shutil.copytree(rootdir / "test-ford-bridge", srcdir)
        outdir = tmp_path / "out"

        app = Sphinx(
            srcdir=str(srcdir),
            confdir=str(srcdir),
            outdir=str(outdir),
            doctreedir=str(tmp_path / "doctrees"),
            buildername="dummy",
            confoverrides={"ford_project_file": str(toml_f_ford_file)},
        )
        app.build()
        domain = app.env.get_domain("f")
        objects = domain.objects

        # Should have populated some modules from the FORD project
        module_names = [fqn for fqn, obj in objects.items() if obj.objtype == "module"]
        assert len(module_names) > 0

    def test_boundproc_links_resolve_in_html(self, toml_f_ford_file, rootdir, tmp_path):
        """Bound-procedure links render as resolved HTML links.

        This guards against regressions where ``:f:func:`~mod.proc``` was emitted
        as unresolved literal text instead of an internal anchor link.
        """
        import shutil

        from sphinx.application import Sphinx

        srcdir = tmp_path / "src"
        shutil.copytree(rootdir / "test-ford-bridge", srcdir)
        outdir = tmp_path / "out"

        (srcdir / "index.rst").write_text(
            """FORD Bridge Test
================

.. f:automodule:: tomlf_de_context
"""
        )

        app = Sphinx(
            srcdir=str(srcdir),
            confdir=str(srcdir),
            outdir=str(outdir),
            doctreedir=str(tmp_path / "doctrees"),
            buildername="html",
            confoverrides={
                "ford_project_file": str(toml_f_ford_file),
                "ford_display": ["public", "protected", "private"],
            },
        )
        app.build()

        html = (outdir / "index.html").read_text()
        assert "Binds to:" in html
        assert 'href="#f-subroutine-tomlf_de_context-push_back"' in html
        assert 'href="#f-function-tomlf_de_context-report1"' in html
        assert "~tomlf_de_context.push_back" not in html
        assert "~tomlf_de_context.report1" not in html
