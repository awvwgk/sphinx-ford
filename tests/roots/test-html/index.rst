HTML Build Test
===============

.. f:module:: html_mod
   :permission: public

   A module for HTML build testing.

   .. f:function:: compute(x, y)

      Compute something.

      :param x: First input
      :ftype x: real
      :intent x: in
      :param y: Second input
      :ftype y: real
      :intent y: in
      :returns: The computed result
      :rtype: real

   .. f:type:: config_type
      :abstract:

      Configuration type.

      .. f:variable:: debug

         Debug flag.

   .. f:subroutine:: initialize(cfg)

      Initialize the config.

      :param cfg: The config to init
      :ftype cfg: type(config_type)
      :intent cfg: inout

   .. f:interface:: parse_iface
      :abstract:

      Abstract parser interface.

References
----------

See :f:mod:`html_mod` for the module.

Use :f:func:`compute` to calculate.

The :f:type:`config_type` holds settings.
