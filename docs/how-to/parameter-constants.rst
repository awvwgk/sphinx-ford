How to document parameter constants and type members
====================================================

This guide shows when to use ``f:variable`` versus ``f:member`` and
how to document ``parameter`` constants clearly.

Document a parameter constant
------------------------------

Use ``f:variable`` with the ``:parameter:`` option. The rendered
heading will show "parameter" instead of "variable":

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:variable:: MAX_ELEMENTS
            :parameter:

            Maximum number of elements allowed.

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:variable} MAX_ELEMENTS
         :parameter:

         Maximum number of elements allowed.
         ```

This renders as:

   .. f:variable:: MAX_ELEMENTS
      :parameter:

      Maximum number of elements allowed.

Document a type component (member)
-----------------------------------

Use ``f:member`` for variables that belong to a derived type.

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:type:: config_t

            .. f:member:: verbose

               Enable verbose output.

            .. f:member:: max_iter

               Maximum iteration count.

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:type} config_t

         ```{f:member} verbose

         Enable verbose output.
         ```

         ```{f:member} max_iter

         Maximum iteration count.
         ```
         ```

This renders as:

   .. f:type:: config_t

      .. f:member:: verbose

         Enable verbose output.

      .. f:member:: max_iter

         Maximum iteration count.

Reference members and parameters
---------------------------------

Use ``:f:var:`` for module-level variables and parameters:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         See :f:var:`MAX_ELEMENTS` for the limit.

   .. tab-item:: MyST

      .. code-block:: markdown

         See {f:var}`MAX_ELEMENTS` for the limit.

This renders as:

   See :f:var:`MAX_ELEMENTS` for the limit.

Use ``:f:mem:`` for type components:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         The :f:mem:`config_t.verbose` flag controls output.

   .. tab-item:: MyST

      .. code-block:: markdown

         The {f:mem}`config_t.verbose` flag controls output.

This renders as:

   The :f:mem:`config_t.verbose` flag controls output.

``:f:var:`` still resolves members for compatibility, but ``:f:mem:``
is preferred because it communicates structure more clearly.

Automatic detection via FORD
-----------------------------

When using the FORD bridge, sphinx-ford automatically:

- Emits ``f:member`` for type component variables
- Detects the Fortran ``parameter`` attribute and adds ``:parameter:``
- Links type names in parameter lists to their definitions
