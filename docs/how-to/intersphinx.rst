How to set up cross-project linking
====================================

This guide shows how to set up links between different documentation
projects.

Link from one sphinx-ford project to another
---------------------------------------------

Standard Sphinx intersphinx works automatically. In the downstream
project's ``conf.py``:

.. code-block:: python

   extensions = ["sphinx_ford", "sphinx.ext.intersphinx"]
   intersphinx_mapping = {
       "toml-f": ("https://toml-f.readthedocs.io/", None),
   }

Use ``:f:mod:`tomlf``` (or the MyST equivalent) in content:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         See :f:mod:`tomlf` for TOML parsing support.

   .. tab-item:: MyST

      .. code-block:: markdown

         See {f:mod}`tomlf` for TOML parsing support.

This renders as:

   See :f:mod:`tomlf` for TOML parsing support.


Link from sphinx-ford to a FORD site
------------------------------------

To link to an existing FORD-generated site, generate ``objects.inv``
from FORD's ``modules.json``:

.. code-block:: python

   from sphinx_ford.ford_parser import (
       load_modules_json, parse_modules_json, write_objects_inv
   )

   data = load_modules_json("path/to/ford/output/modules.json")
   entities = parse_modules_json(data, "https://stdlib.fortran-lang.org/")
   write_objects_inv(entities, "stdlib-objects.inv", "stdlib")

Then add it to intersphinx:

.. code-block:: python

   intersphinx_mapping = {
       "stdlib": ("https://stdlib.fortran-lang.org/", "stdlib-objects.inv"),
   }

Link from FORD to sphinx-ford pages
------------------------------------

Set ``ford_export_modules_json = True`` in ``conf.py``. After building,
a ``modules.json`` file appears in the output directory. FORD projects
can reference it with their ``external`` config option.