Installing and using sphinx-ford
================================

This guide shows the minimal setup to install and enable sphinx-ford.


Install sphinx-ford with pip
----------------------------

The sphinx-ford package is available on PyPI and can be installed with pip::

    pip install sphinx-ford

To include the optional FORD bridge, install the ``auto`` extra::

    pip install sphinx-ford[auto]



Install from GitHub
-------------------

You can also install the latest development version directly from GitHub::

    pip install git+https://github.com/awvwgk/sphinx-ford.git



Enable in Sphinx
----------------

To enable sphinx-ford in your Sphinx project, add it to the ``extensions`` list in your ``conf.py``:

.. code-block:: python
   :caption: conf.py

   extensions = ["sphinx_ford"]

Then you can use the ``f`` domain and FORD bridge directives in your reStructuredText files.
See the other how-to guides for examples of how to use these features.