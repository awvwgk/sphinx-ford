"""Sphinx domain for Fortran with FORD bridge."""

__version__ = "0.1.0"


def setup(app):
    """Register the Fortran domain with Sphinx."""
    from sphinx_ford.domain import FortranDomain

    # Guard against conflict with sphinx-fortran which also uses 'f'
    if "f" in app.registry.domains:
        from sphinx.errors import ExtensionError

        raise ExtensionError(
            "sphinx-ford: domain 'f' is already registered (possibly by sphinx-fortran). "
            "Cannot load both extensions simultaneously."
        )

    app.add_domain(FortranDomain)

    # Register FORD bridge (config values, directives, event handlers)
    from sphinx_ford.ford_bridge import setup as ford_bridge_setup

    ford_bridge_setup(app)

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
