"""Integration tests: full HTML builds."""

import pytest
from sphinx import addnodes


class TestHTMLBuild:
    """Test full HTML output."""

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_build_succeeds(self, app):
        """HTML build completes without errors."""
        app.build()
        assert (app.outdir / "index.html").exists()

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_contains_module(self, app):
        """HTML output contains the module name."""
        app.build()
        content = (app.outdir / "index.html").read_text()
        assert "html_mod" in content

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_contains_function(self, app):
        """HTML output contains the function."""
        app.build()
        content = (app.outdir / "index.html").read_text()
        assert "compute" in content

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_contains_type(self, app):
        """HTML output contains the type."""
        app.build()
        content = (app.outdir / "index.html").read_text()
        assert "config_type" in content

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_contains_abstract_type_prefix(self, app):
        """Abstract types render with the abstract type prefix."""
        app.build()
        doctree = app.env.get_doctree("index")
        type_sig = None
        for sig in doctree.findall(addnodes.desc_signature):
            if "f-type-html_mod-config_type" in (sig.get("ids") or []):
                type_sig = sig
                break

        assert type_sig is not None
        annotations = [
            n.astext() for n in type_sig.findall(addnodes.desc_annotation) if n.astext().strip()
        ]
        assert any("abstract type" in text for text in annotations)

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_contains_abstract_interface_prefix(self, app):
        """Abstract interfaces render with the abstract interface prefix."""
        app.build()
        doctree = app.env.get_doctree("index")
        iface_sig = None
        for sig in doctree.findall(addnodes.desc_signature):
            if "f-interface-html_mod-parse_iface" in (sig.get("ids") or []):
                iface_sig = sig
                break

        assert iface_sig is not None
        annotations = [
            n.astext() for n in iface_sig.findall(addnodes.desc_annotation) if n.astext().strip()
        ]
        assert any("abstract interface" in text for text in annotations)

    @pytest.mark.sphinx("html", testroot="html")
    def test_html_cross_references_are_links(self, app):
        """Cross-references produce <a> tags."""
        app.build()
        content = (app.outdir / "index.html").read_text()
        # The cross-references should produce internal links
        assert 'href="#' in content

    @pytest.mark.sphinx("html", testroot="module")
    def test_objects_inv_generated(self, app):
        """objects.inv is generated for intersphinx."""
        app.build()
        assert (app.outdir / "objects.inv").exists()

    @pytest.mark.sphinx("html", testroot="html")
    def test_module_has_toc_object_entry(self, app):
        """Fortran module signatures expose TOC object metadata."""
        app.build()
        doctree = app.env.get_doctree("index")
        module_sig = None
        for sig in doctree.findall(addnodes.desc_signature):
            if "f-module-html_mod" in (sig.get("ids") or []):
                module_sig = sig
                break

        assert module_sig is not None
        assert module_sig.get("_toc_parts") == ("html_mod",)
        assert module_sig.get("_toc_name") == "html_mod"
