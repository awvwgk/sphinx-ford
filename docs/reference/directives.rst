Directives reference
====================

All directives use the ``f:`` domain prefix.

Entity directives
-----------------

All entity directives accept the following **common options**:

``:module:``
  set the parent module context
``:permission:``
  ``public``, ``private``, or ``protected``
``:noindex:``
  suppress index entry generation
``:noindexentry:``
  suppress the directive from the general index

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Directive
     - Fortran entity
     - Additional options
   * - ``f:module``
     - Module
     - (common options only)
   * - ``f:submodule``
     - Submodule
     - (common options only)
   * - ``f:program``
     - Program
     - (common options only)
   * - ``f:function``
     - Function
     - (common options only)
   * - ``f:subroutine``
     - Subroutine
     - (common options only)
   * - ``f:type``
     - Derived type
     - ``:extends:``, ``:abstract:``
   * - ``f:variable``
     - Variable
     - ``:parameter:``
   * - ``f:member``
     - Type component (data member)
     - (common options only)
   * - ``f:interface``
     - Interface
     - ``:generic:``, ``:abstract:``
   * - ``f:enum``
     - Enum
     - (common options only)
   * - ``f:boundproc``
     - Bound procedure
     - ``:deferred:``, ``:generic:``
   * - ``f:blockdata``
     - Block data
     - (common options only)
   * - ``f:common``
     - Common block
     - (common options only)
   * - ``f:namelist``
     - Namelist
     - (common options only)

Usage examples
~~~~~~~~~~~~~~

Module with a function

.. code-block:: rst

   .. f:module:: math_utils

      .. f:function:: pure add(a, b)

Rendered output:

   .. f:module:: math_utils

      .. f:function:: pure add(a, b)

Type with members

.. code-block:: rst

   .. f:currentmodule:: ref__directives
   .. f:type:: point_t

      .. f:member:: x
      .. f:member:: y

Rendered output:

   .. f:type:: point_t

      .. f:member:: x
      .. f:member:: y

Generic interface

.. code-block:: rst

   .. f:interface:: operator(+)
      :generic:

Rendered output:

   .. f:currentmodule:: ref__directives
   .. f:interface:: operator(+)
      :generic:

- Interface heading ``operator(+)`` appears and is marked generic.

Parameter constant

.. code-block:: rst

   .. f:variable:: PI
      :parameter:

Rendered output:

   .. f:currentmodule:: ref__directives
   .. f:variable:: PI
      :parameter:

Context directives
------------------

``f:currentmodule``
    Set the current module context without producing output.
    Use ``None`` to clear the context.

    Example

    .. code-block:: rst

       .. f:currentmodule:: my_module

FORD bridge directives
----------------------

``f:automodule``
    Auto-document a single module from FORD sources.
    Requires ``ford_project_file`` or ``ford_project_files``.

    Options:

    ``:visibility:``
      filter entities by permission level.
      Comma-separated list, e.g. ``public`` or ``public,protected``.
      Overrides ``ford_display``.
    ``:case:``
      normalize Fortran keyword case for this directive.
      ``lower`` or ``upper``.  Overrides ``ford_case``.

    Example:

    .. code-block:: rst

       .. f:automodule:: stdlib_ascii

       .. f:automodule:: dbcsr_api
          :case: upper

       .. f:automodule:: internal_mod
          :visibility: public,protected

``f:autoproject``
    Auto-document all modules from a FORD project.
    Requires ``ford_project_file`` or ``ford_project_files``.

    Options:

    ``:visibility:``
      filter entities by permission level (same as ``f:automodule``).
    ``:case:``
      normalize Fortran keyword case (same as ``f:automodule``).

    Example:

    .. code-block:: rst

       .. f:autoproject::
          :visibility: public


Doc fields (procedures)
-----------------------

Inside ``f:function`` and ``f:subroutine``:

``:param name:`` (aliases: ``:p:``, ``:argument:``, ``:arg:``)
  argument description
``:ftype name:``
  argument Fortran type
``:intent name:``
  ``in``, ``out``, or ``inout``
``:optional name:``
  mark argument as optional
``:returns:``
  (alias: ``:return:``) return value description
``:rtype:``
  return type
