How to auto-document a FORD project
===================================

This guide shows the fastest way to enable FORD-based auto-documentation.

Configure a single FORD project
-------------------------------

Set ``ford_project_file`` in ``conf.py``:

.. code-block:: python

   extensions = ["sphinx_ford"]
   ford_project_file = "docs.md"

Document one module with ``f:automodule``:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:automodule:: my_module

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:automodule} my_module
         ```

Document all modules with ``f:autoproject``:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:autoproject::

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:autoproject}
         ```

Configure multiple FORD projects
--------------------------------

Use ``ford_project_files`` when a site combines several projects.

.. code-block:: python

   ford_project_files = [
       "project1/docs.md",
       {
           "path": "project2/DBCSR.md",
           "vars": {"CMAKE_SOURCE_DIR": "project2"},
           "preprocess": False,
       },
   ]

Each entry can be either:

- a path string
- a dict with ``path``, ``vars``, and ``preprocess`` overrides

Handle CMake-templated FORD files
---------------------------------

If the FORD project file contains ``@VAR@`` placeholders, pass values
through ``ford_project_vars``:

.. code-block:: python

   ford_project_vars = {
       "CMAKE_SOURCE_DIR": "/path/to/project",
       "PROJECT_VERSION": "1.0.0",
   }

Disable preprocessing
---------------------

Disable preprocessing when tools like ``cpp`` or ``fypp`` are not
available in the build environment:

.. code-block:: python

   ford_preprocess = False

sphinx-ford will still document files that do not require preprocessing.

Export for FORD cross-linking
-----------------------------

Enable JSON export so external FORD projects can link back:

.. code-block:: python

   ford_export_modules_json = True

This writes a ``modules.json`` to the output directory after every
build. See :doc:`intersphinx` for details on cross-project linking.

For the complete list of configuration options, see the
:doc:`/reference/configuration`.
