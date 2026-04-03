How to structure nested module documentation
============================================

This guide shows a clear pattern for documenting modules with nested
types, procedures, and members.

Define entities inside ``f:module``
-----------------------------------

Put related directives inside the module body. sphinx-ford then builds
fully qualified names automatically (for example ``my_module.compute``).

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:module:: my_module
            :permission: public

            Module description.

            .. f:function:: compute(x, y)

               :param x: Input x
               :ftype x: real
               :intent x: in

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:module} my_module
         :permission: public

         Module description.

         ```{f:function} compute(x, y)

         :param x: Input x
         :ftype x: real
         :intent x: in
         ```
         ```

This renders as:

   .. f:module:: my_module
      :permission: public

      Module description.

      .. f:function:: compute(x, y)

         :param x: Input x
         :ftype x: real
         :intent x: in


Document members and bound procedures in ``f:type``
---------------------------------------------------

Use ``f:member`` for type components and ``f:boundproc`` for bound
procedures.

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:type:: config_t
            :extends: base_t

            .. f:member:: verbose

               Enable verbose output.

            .. f:boundproc:: validate
               :deferred:

               Check configuration consistency.

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:type} config_t
         :extends: base_t

         ```{f:member} verbose

         Enable verbose output.
         ```

         ```{f:boundproc} validate
         :deferred:

         Check configuration consistency.
         ```
         ```

This renders as:

   .. f:currentmodule:: howto__document_module

   .. f:type:: config_t
      :extends: base_t

      .. f:member:: verbose

         Enable verbose output.

      .. f:boundproc:: validate
         :deferred:

         Check configuration consistency.

Set context across split files with ``f:currentmodule``
-------------------------------------------------------

If module content is split across files, set context without emitting
new output.

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:currentmodule:: my_module

         :f:func:`compute` now resolves to ``my_module.compute``.

         Use ``None`` to clear the context.

         .. f:currentmodule:: None

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:currentmodule} my_module
         ```

         {f:func}`compute` now resolves to `my_module.compute`.

         Use `None` to clear the context.

         ```{f:currentmodule} None
         ```

This renders as

   .. f:currentmodule:: my_module

   :f:func:`compute` now resolves to ``my_module.compute``.

   Use ``None`` to clear the context.

   .. f:currentmodule:: None