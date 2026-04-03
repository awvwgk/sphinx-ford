Configuration reference
=======================

All configuration values are set in ``conf.py``.

Extension setup
---------------

.. code-block:: python

   extensions = ["sphinx_ford"]


FORD bridge options
-------------------

``ford_project_file``
   Path to a single FORD project file (usually a ``.md`` file).
   When set, FORD parses the Fortran sources at build time.

   Default: ``None``

``ford_project_files``
   List of FORD project files to load.  Each entry can be a string
   path or a dict with per-project overrides:

   .. code-block:: python

      ford_project_files = [
          "path/to/project1/docs.md",
          {
              "path": "path/to/project2/DBCSR.md",
              "vars": {"CMAKE_SOURCE_DIR": "/path/to/project2"},
              "preprocess": False,
          },
      ]

   Modules from all projects are merged into a single pool for
   ``f:automodule`` lookup.

   Default: ``[]``

``ford_project_vars``
   Dictionary of ``{VAR: value}`` for substituting ``@VAR@`` patterns
   in CMake-templated FORD project files.  Applied to projects loaded
   via ``ford_project_file`` (per-project overrides use the ``vars``
   key in ``ford_project_files`` entries instead).

   Default: ``{}``

   Example:

   .. code-block:: python

      ford_project_vars = {
          "CMAKE_SOURCE_DIR": "/path/to/project",
          "dbcsr_VERSION": "2.9.1",
      }

``ford_preprocess``
   Whether to run the Fortran preprocessor on files with
   ``fpp_extensions``. When ``True`` (default), sphinx-ford detects
   the preprocessor command from the FORD project file and verifies
   it is available.  If the preprocessor is not found, an error is
   raised with installation instructions.  Set to ``False`` to skip
   preprocessing entirely.

   Default: ``True``

``ford_display``
   Default visibility filter for ``f:automodule`` and ``f:autoproject``
   directives.  A list of permission levels to include, e.g.
   ``["public"]`` or ``["public", "protected"]``.  Entities whose
   ``permission`` is not in the set are hidden.  Falls back to the
   FORD project's own ``display`` setting when not set.

   Can be overridden per-directive with the ``:visibility:`` option.

   Default: ``None`` (use FORD project setting)

   Example:

   .. code-block:: python

      ford_display = ["public", "protected"]

``ford_case``
   Normalize Fortran keyword case in auto-generated documentation.
   Controls how type names, attributes (``pointer``, ``allocatable``),
   intent qualifiers, and procedure prefixes (``pure``, ``elemental``)
   are displayed.

   ``"lower"``
     lowercase all keywords
   ``"upper"``
     uppercase all keywords
   ``None``
     preserve original case from source

   Can be overridden per-directive with the ``:case:`` option.

   Default: ``None``

   Example:

   .. code-block:: python

      ford_case = "lower"

``ford_export_modules_json``
   If ``True``, write a FORD-compatible ``modules.json`` to the output
   directory after building. This enables FORD projects to link back
   to sphinx-ford docs.

   Default: ``False``
