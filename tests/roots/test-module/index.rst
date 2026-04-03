Test Module
===========

.. f:module:: test_mod
   :permission: public

   A test module.

   .. f:function:: test_func(x, y)

      A test function.

      :param x: First argument
      :ftype x: integer
      :intent x: in
      :param y: Second argument
      :ftype y: real
      :intent y: in
      :returns: The result
      :rtype: real

   .. f:subroutine:: test_sub(a)

      A test subroutine.

      :param a: Argument
      :ftype a: character(len=*)
      :intent a: in

   .. f:type:: test_type
      :extends: base_type

      A test derived type.

      .. f:variable:: value

         A component variable.

      .. f:boundproc:: get_value
         :deferred:

         Get the value.

   .. f:interface:: test_iface
      :generic:

      A generic interface.

   .. f:variable:: module_var

      A module-level variable.

   .. f:variable:: FMT_INT = '((i0))'
      :parameter:

      Format string for integers.

.. f:module:: another_mod

   Another module.
