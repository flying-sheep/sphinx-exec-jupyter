# sphinx-exec-jupyter

[![Documentation Status](https://readthedocs.org/projects/sphinx-exec-jupyter/badge/?version=latest)](https://sphinx-exec-jupyter.readthedocs.io/en/latest/)

This Sphinx extension allows you to execute Jupyter notebooks and include their output in your documentation.

## Installation

Install or depend on
`sphinx-exec-jupyter @ git+https://github.com/flying-sheep/sphinx-exec-jupyter.git`,
optionally with the `holoviews` extra (see below).
Then enable this extension in your `conf.py`:

```python
extensions = [
    "sphinx_exec_jupyter",
]
```

## Directives

### `exec-jupyter`

Executes a Jupyter notebook cell and includes its output:

```rst
..  exec-jupyter::

    import numpy as np
    np.random.rand(4)
```

### `holoviews`

Enable by installing the `holoviews` extra by depending on
`sphinx-exec-jupyter[holoviews] @ git+https://github.com/flying-sheep/sphinx-exec-jupyter.git`

Embeds a HoloViews plot:

```rst
..  holoviews::
    :backends: bokeh,matplotlib

    hv.Curve([1, 2, 3, 2, 1])
```

The default for `backends` is defined by a Sphinx `conf.py` setting:
`holoviews_backends = ['bokeh']`

For detailed documentation, visit [Read the Docs](https://sphinx-exec-jupyter.readthedocs.io/).
