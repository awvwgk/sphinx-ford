How to cross-reference Fortran entities
=======================================

This guide shows how to create reliable, clickable links between
Fortran entities.

Reference by entity name
------------------------

Use the role that matches the entity type. For a function:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         See :f:func:`compute` for the algorithm.

   .. tab-item:: MyST

      .. code-block:: markdown

         See {f:func}`compute` for the algorithm.


This renders as

   See :f:func:`compute` for the algorithm.

For the full list of roles, see the :doc:`/reference/roles`.

Reference an entity in another module
--------------------------------------

Use dot-separated qualified names:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         Uses :f:func:`physics.kinetic_energy` internally.

   .. tab-item:: MyST

      .. code-block:: markdown

         Uses {f:func}`physics.kinetic_energy` internally.

This renders as

   Uses :f:func:`physics.kinetic_energy` internally.

If a ``f:currentmodule`` is active, unqualified names are searched
in that module first.

Handle case-insensitive names
-----------------------------

Fortran is case-insensitive, and so are sphinx-ford cross-references.
All of these resolve to the same entity:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         :f:mod:`MY_MODULE`
         :f:mod:`my_module`
         :f:mod:`My_Module`

   .. tab-item:: MyST

      .. code-block:: markdown

         {f:mod}`MY_MODULE`
         {f:mod}`my_module`
         {f:mod}`My_Module`

This renders as:

   :f:mod:`MY_MODULE`
   :f:mod:`my_module`
   :f:mod:`My_Module`

Reference type components
-------------------------

Type components (``f:member``) and bound procedures (``f:boundproc``)
are qualified through their parent module, not the type:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         :f:mem:`my_module.component_name`

   .. tab-item:: MyST

      .. code-block:: markdown

         {f:mem}`my_module.component_name`

This renders as:

   :f:mem:`my_module.component_name`