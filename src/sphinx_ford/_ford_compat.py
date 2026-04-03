"""Compatibility layer for different FORD versions.

Supports:
- FORD 6.x (6.1.15): ford.parse_arguments(cmd, docs, dir) returns (dict, html, md)
- FORD 7.x (7.0.13): ford.load_settings(docs, dir) + ford.parse_arguments(cmd, docs, settings, dir) returns (settings, html)
"""

from __future__ import annotations

import contextlib
import io
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from sphinx.errors import ExtensionError

logger = logging.getLogger(__name__)

_ford_version: int | None = None


def get_ford_major_version() -> int:
    """Detect FORD major version."""
    global _ford_version
    if _ford_version is not None:
        return _ford_version

    import ford

    # FORD 7 has load_settings; FORD 6 does not
    if hasattr(ford, "load_settings"):
        _ford_version = 7
    else:
        _ford_version = 6

    logger.debug("Detected FORD major version: %d", _ford_version)
    return _ford_version


def _check_preprocessor(proj_data: Any, preprocess: bool) -> None:
    """Validate that the required preprocessor is available.

    Checks the preprocessor command from the FORD project settings.
    If preprocessing is needed (fpp_extensions is non-empty and preprocess
    is True), verifies the preprocessor command is on PATH.

    Parameters
    ----------
    proj_data
        FORD project settings (dict for v6, ProjectSettings for v7).
    preprocess
        Whether preprocessing is requested.

    Raises
    ------
    ExtensionError
        If the preprocessor is required but not found.
    """
    if not preprocess:
        return

    # Extract settings from dict (FORD 6) or object (FORD 7)
    if isinstance(proj_data, dict):
        fpp_extensions = proj_data.get("fpp_extensions", [])
        pp_setting = proj_data.get("preprocessor", "")
        do_preprocess = proj_data.get("preprocess", True)
    else:
        fpp_extensions = getattr(proj_data, "fpp_extensions", [])
        pp_setting = getattr(proj_data, "preprocessor", "")
        do_preprocess = getattr(proj_data, "preprocess", True)

    if not fpp_extensions or not do_preprocess:
        return

    # The preprocessor setting is either a string or a list
    if isinstance(pp_setting, list):
        pp_cmd = pp_setting[0] if pp_setting else ""
    elif isinstance(pp_setting, str):
        pp_cmd = pp_setting.split()[0] if pp_setting else ""
    else:
        pp_cmd = str(pp_setting).split()[0] if pp_setting else ""

    if not pp_cmd:
        return

    # Check if the preprocessor executable is on PATH
    if shutil.which(pp_cmd) is not None:
        logger.info(
            "sphinx-ford: preprocessor '%s' found, preprocessing enabled for extensions: %s",
            pp_cmd,
            fpp_extensions,
        )
        return

    # Try running it directly (some preprocessors are shell builtins or
    # have paths embedded in the command)
    try:
        full_cmd = pp_setting if isinstance(pp_setting, list) else pp_setting.split()
        subprocess.run(
            full_cmd + ["/dev/null"],
            capture_output=True,
            timeout=5,
            check=True,
        )
        logger.info(
            "sphinx-ford: preprocessor '%s' works, preprocessing enabled",
            pp_cmd,
        )
        return
    except (subprocess.CalledProcessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass

    # Preprocessor not available
    raise ExtensionError(
        f"sphinx-ford: preprocessor '{pp_cmd}' is required but not found.\n"
        f"  The FORD project file specifies:\n"
        f"    preprocessor: {pp_setting}\n"
        f"    fpp_extensions: {fpp_extensions}\n"
        f"  To fix this, either:\n"
        f"    1. Install '{pp_cmd}' (e.g., 'pip install {pp_cmd}' or "
        f"'apt install {pp_cmd}')\n"
        f"    2. Set 'ford_preprocess = False' in conf.py to skip "
        f"preprocessing\n"
        f"    3. Use the per-project override: "
        f'{{"path": "...", "preprocess": False}}'
    )


def load_ford_project(
    project_file: str | Path,
    variables: dict[str, str] | None = None,
    preprocess: bool = True,
) -> Any:
    """Load a FORD project, handling version differences.

    Parameters
    ----------
    project_file
        Path to the FORD project file (.md)
    variables
        Dict of @VAR@ for value substitutions for CMake-templated files
    preprocess
        Whether to run the Fortran preprocessor

    Returns
    -------
    ford.fortran_project.Project
    """
    import ford
    import ford.fortran_project

    project_path = Path(project_file).resolve()

    with open(project_path) as f:
        content = f.read()

    # Substitute CMake-style variables
    if variables:
        for key, value in variables.items():
            content = content.replace(f"@{key}@", value)

    directory = str(project_path.parent)
    version = get_ford_major_version()

    stdout_capture = io.StringIO()

    if version >= 7:
        proj_data = _load_v7(ford, content, directory, preprocess, stdout_capture)
    else:
        proj_data = _load_v6(ford, content, directory, preprocess, stdout_capture)

    # Validate that the preprocessor is available before parsing sources
    _check_preprocessor(proj_data, preprocess)

    # Enable debug mode to continue on parse errors
    if isinstance(proj_data, dict):
        proj_data["dbg"] = True
    elif hasattr(proj_data, "dbg"):
        proj_data.dbg = True

    # Monkey-patch FORD 6.1.15's broken error handler:
    # Project.__init__ line 121 does `e.args[0]` on NotImplementedError()
    # which has no args, causing IndexError. Patch sourceform to add an arg.
    if version < 7:
        _orig_cleanup = ford.sourceform.FortranContainer._cleanup

        def _safe_cleanup(self):
            try:
                _orig_cleanup(self)
            except NotImplementedError:
                raise NotImplementedError(
                    f"Unsupported source construct in {getattr(self, 'name', '?')}"
                )

        ford.sourceform.FortranContainer._cleanup = _safe_cleanup

    # Create the Project: catch FORD bugs and continue with partial data
    with contextlib.redirect_stdout(stdout_capture):
        try:
            project = ford.fortran_project.Project(proj_data)
        except (IndexError, NotImplementedError, AttributeError) as e:
            logger.warning(
                "FORD project parsing partially failed (%s: %s), some modules may be missing",
                type(e).__name__,
                e,
            )

            # Create empty project-like object as fallback
            class _EmptyProject:
                modules = []
                files = []

            project = _EmptyProject()

    # Restore original method
    if version < 7:
        ford.sourceform.FortranContainer._cleanup = _orig_cleanup

    return project


def _load_v6(
    ford: Any,
    content: str,
    directory: str,
    preprocess: bool,
    stdout_capture: io.StringIO,
) -> dict:
    """Load settings using FORD 6.x API."""
    with contextlib.redirect_stdout(stdout_capture):
        proj_data, proj_docs_html, md = ford.parse_arguments(
            command_line_args={},
            proj_docs=content,
            directory=directory,
        )

    if not preprocess:
        proj_data["fpp_extensions"] = []
        proj_data["preprocess"] = False

    return proj_data


def _load_v7(
    ford: Any,
    content: str,
    directory: str,
    preprocess: bool,
    stdout_capture: io.StringIO,
) -> Any:
    """Load settings using FORD 7.x API."""
    with contextlib.redirect_stdout(stdout_capture):
        proj_docs, settings = ford.load_settings(content, directory)
        settings, proj_docs_html = ford.parse_arguments({}, proj_docs, settings, directory)

    if not preprocess:
        settings.fpp_extensions = []

    return settings
