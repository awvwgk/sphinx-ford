Auto-documenting Fortran sources with FORD
==========================================

In this tutorial we connect sphinx-ford to FORD so Fortran sources are
parsed and documented automatically.

We assume we completed the :doc:`getting started tutorial
</tutorials/getting-started>` and have a working Sphinx project.

Installing FORD
---------------

We install FORD alongside sphinx-ford::

    pip install ford

FORD is a Fortran documentation tool that knows how to parse Fortran
source files and extract modules, types, procedures, and doc comments.
sphinx-ford uses FORD's parser to feed data into the Fortran domain.

Creating a FORD project file
-----------------------------

FORD uses a Markdown project file that describes where our Fortran
sources live. We create ``docs.md`` at the root of our project:

.. code-block:: markdown

   ---
   project: My Fortran Library
   src_dir: ./src
   ---

   This is our library's FORD project file.

The YAML header tells FORD to look for ``.f90`` files in ``./src``.

Configuring the bridge
----------------------

We add the project file path to our ``conf.py``:

.. code-block:: python

   extensions = ["sphinx_ford"]
   ford_project_file = "docs.md"

Using automodule
----------------

Now we can auto-document any module found in our sources. We replace
the manual directives with a single line per module:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         API Reference
         =============

         .. f:automodule:: physics

   .. tab-item:: MyST

      .. code-block:: markdown

         # API Reference

         ```{f:automodule} physics
         ```

   .. tab-item:: Rendered output

      - The full ``physics`` module page is generated from FORD data.
      - Nested entities (types, procedures, interfaces, variables) are emitted automatically.

When we build, sphinx-ford asks FORD to parse our Fortran sources,
finds the ``physics`` module, and generates the full documentation:
types, functions, subroutines, interfaces, and all their parameters.

Building and viewing the result
-------------------------------

We run::

    sphinx-build docs _build/html

We open ``_build/html/index.html`` and see our module fully documented
with all procedures, their argument types, intents, and doc comments.
This is exactly matching what FORD would show, but rendered as a Sphinx page
with cross-references, search, and our chosen theme.

Rendered output:

- Module page generated directly from Fortran sources.
- Procedures rendered with argument/intent/type fields.
- Cross-references resolve through the Fortran domain.

What we have built
------------------

We now have an automated documentation pipeline:

- Fortran source code, FORD parser, sphinx-ford domain, HTML
- Doc comments from the source appear as formatted descriptions
- Type names in parameters are linked to their definitions
- Interfaces show all their member procedures

For more advanced scenarios, like multiple projects, CMake-templated FORD
files, or preprocessing, see :doc:`/how-to/ford-project`.
