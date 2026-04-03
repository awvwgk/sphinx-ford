Sphinx-FORD bridge
==================

This repository contains the sphinx-ford bridge.
It provides a Sphinx domain for documenting Fortran code and the possibility to generate documentation automatically from FORD projects.

Installation
------------

Install the package from PyPI:

```bash
pip install sphinx-ford[auto]
```

Usage
-----

To use the sphinx-ford bridge, add `sphinx_ford` to the `extensions` list in your Sphinx `conf.py` file:

```python
extensions = [
    'sphinx_ford',
    # other extensions...
]
```

This will enable the Fortran domain and allow you to use the provided directives and roles to document your Fortran code.

Add your FORD project to the Sphinx configuration:

```python
ford_project_file = "docs.md"
```

To automatically document your Fortran code

```rst
.. f:automodule:: physics
```

License
-------

This project is avaialble under an Apache 2.0 license. See the LICENSE file for details.