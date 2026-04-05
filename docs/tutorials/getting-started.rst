Getting started with sphinx-ford
================================

In this tutorial we install sphinx-ford, write a small module page,
and build HTML output. The result is a clean baseline project with
working directives and cross-references.

Installing sphinx-ford
----------------------

We start by installing the package::

    pip install sphinx-ford

.. note::

   We do not need FORD installed for this tutorial, the Fortran domain
   works entirely on its own. We will use FORD's auto-documentation
   bridge in the :doc:`next tutorial </tutorials/ford-bridge>`.

Setting up the project
----------------------

We create a minimal Sphinx project. If we already have one, we skip
to the next section::

    mkdir fortran-docs && cd fortran-docs
    sphinx-quickstart --quiet --project "My Fortran Docs" --author "me"

Now we enable sphinx-ford by adding it to ``conf.py``:

.. code-block:: python

   extensions = ["sphinx_ford"]

Writing our first module
------------------------

We open ``index.rst`` (or ``index.md`` for MyST) and replace its
contents with:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         My Fortran Library
         ==================

         .. f:module:: physics
            :permission: public

            Physical constants and utility routines.

            .. f:variable:: speed_of_light
               :parameter:

               Speed of light in vacuum (m/s).

            .. f:function:: kinetic_energy(mass, velocity)

               Compute kinetic energy.

               :param mass: Object mass
               :ftype mass: real(dp)
               :intent mass: in
               :param velocity: Object velocity
               :ftype velocity: real(dp)
               :intent velocity: in
               :rtype: real(dp)

   .. tab-item:: MyST

      .. code-block:: markdown

         # My Fortran Library

         ````{f:module} physics
         :permission: public

         Physical constants and utility routines.

         ```{f:variable} speed_of_light
         :parameter:

         Speed of light in vacuum (m/s).
         ```

         ```{f:function} kinetic_energy(mass, velocity)

         :param mass: Object mass
         :ftype mass: real(dp)
         :intent mass: in
         :param velocity: Object velocity
         :ftype velocity: real(dp)
         :intent velocity: in
         :rtype: real(dp)
         ```
         ````

Building and viewing the result
-------------------------------

We run the Sphinx build::

    sphinx-build . _build/html

We open ``_build/html/index.html`` in a browser. We should see:

- A **module physics** heading with the description we wrote.
- A **parameter speed_of_light** entry (because we used ``:parameter:``).
- A **function kinetic_energy(mass, velocity)** with typed parameters.

This renders as:

   .. f:module:: physics
      :permission: public

      Physical constants and utility routines.

      .. f:variable:: speed_of_light
         :parameter:

         Speed of light in vacuum (m/s).

      .. f:function:: kinetic_energy(mass, velocity)

         Compute kinetic energy.

         :param mass: Object mass
         :ftype mass: real(dp)
         :intent mass: in
         :param velocity: Object velocity
         :ftype velocity: real(dp)
         :intent velocity: in
         :rtype: real(dp)

Adding cross-references
-----------------------

We add a second module that references the first. We append to our
file:

.. tab-set::

   .. tab-item:: reStructuredText

      .. code-block:: rst

         .. f:module:: simulation

            Simulation routines. Uses :f:mod:`physics`.

            .. f:subroutine:: run(dt)

               Run a simulation step using :f:func:`physics.kinetic_energy`.

   .. tab-item:: MyST

      .. code-block:: markdown

         ```{f:module} simulation

         Simulation routines. Uses {f:mod}`physics`.

         ```{f:subroutine} run(dt)

         Run a simulation step using {f:func}`physics.kinetic_energy`.
         ```
         ```

We rebuild and notice that ``physics`` and ``physics.kinetic_energy``
are now clickable links pointing back to their definitions above.

This renders as:

   .. f:module:: simulation

      Simulation routines. Uses :f:mod:`physics`.

      .. f:subroutine:: run(dt)

         Run a simulation step using :f:func:`physics.kinetic_energy`.

What we have created
--------------------

We now have a Sphinx site that documents Fortran code with:

- Modules, functions, variables and types as first-class entities
- Automatic cross-referencing between entities
- Module, procedure and type indices (see the sidebar)

Next, we can :doc:`connect FORD to auto-generate documentation
from Fortran source files </tutorials/ford-bridge>`, or explore the
:doc:`reference </reference/directives>` for all available directives.
