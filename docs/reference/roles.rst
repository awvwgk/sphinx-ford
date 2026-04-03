Roles reference
===============

All roles use the ``f:`` domain prefix and are case-insensitive.

.. list-table::
   :header-rows: 1
   :widths: 20 20 30

   * - Role
     - Target type
     - Example
   * - ``:f:mod:``
     - Module
     - ``:f:mod:`my_module```
   * - ``:f:submod:``
     - Submodule
     - ``:f:submod:`child_mod```
   * - ``:f:prog:``
     - Program
     - ``:f:prog:`main_program```
   * - ``:f:func:``
     - Function
     - ``:f:func:`compute```
   * - ``:f:subr:``
     - Subroutine
     - ``:f:subr:`initialize```
   * - ``:f:type:``
     - Derived type
     - ``:f:type:`config_t```
   * - ``:f:var:``
     - Variable
     - ``:f:var:`count```
   * - ``:f:mem:``
     - Type component
     - ``:f:mem:`my_type%component```
   * - ``:f:iface:``
     - Interface
     - ``:f:iface:`generic_op```
   * - ``:f:enum:``
     - Enum
     - ``:f:enum:`color```
   * - ``:f:bp:``
     - Bound procedure
     - ``:f:bp:`method```
   * - ``:f:block:``
     - Block data
     - ``:f:block:`blk_data```
   * - ``:f:common:``
     - Common block
     - ``:f:common:`shared```
   * - ``:f:nml:``
     - Namelist
     - ``:f:nml:`params```

Name resolution
---------------

1. Direct match by FQN (e.g., ``my_module.compute``)
2. Search with module context prefix
3. Suffix match across all objects

All lookups are case-insensitive.
