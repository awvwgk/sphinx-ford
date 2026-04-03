"""Sphinx configuration for sphinx-ford documentation."""

import sys
from pathlib import Path

project = "sphinx-ford"
author = "Sebastian Ehlert"
copyright = f"2026, {author}"

extensions = [
    "sphinx_ford",
    "sphinx_design",
    "myst_parser",
]

templates_path = []
exclude_patterns = ["_build", "_examples_src"]

html_theme = "sphinx_book_theme"

# Import the fetch helper (lives next to conf.py)
sys.path.insert(0, str(Path(__file__).parent))
from fetch_examples import EXAMPLES, fetch  # noqa: E402

# Build list of FORD project files for multi-project support
ford_project_files = []

for name, info in EXAMPLES.items():
    try:
        project_dir = fetch(name)
        ford_file = str(project_dir / info["ford_file"])

        # Each entry can be a dict with per-project overrides
        entry = {"path": ford_file}

        # Handle preprocessing (e.g., stdlib uses fypp)
        if info.get("preprocess") is False:
            entry["preprocess"] = False

        # Handle CMake template variables (e.g., dbcsr)
        if "vars" in info:
            vars_dict = dict(info["vars"])
            # Auto-set common CMake variables
            vars_dict.setdefault("CMAKE_SOURCE_DIR", str(project_dir))
            vars_dict.setdefault("CMAKE_BINARY_DIR", str(project_dir / "_build"))
            # Set version from dirname if available
            dirname = info.get("dirname", "")
            if "-" in dirname:
                version = dirname.rsplit("-", 1)[-1]
                vars_dict.setdefault("dbcsr_VERSION", version)
            entry["vars"] = vars_dict

        ford_project_files.append(entry)
        print(f"sphinx-ford docs: loaded {name} from {ford_file}")
    except Exception as e:
        print(f"Warning: could not fetch {name}: {e}")

# Keep ford_project_file as None, we use ford_project_files instead
ford_project_file = None
