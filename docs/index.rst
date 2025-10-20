``sphinx_exec_jupyter``
=======================

The ``sphinx-exec-jupyter`` Sphinx extension allows you to execute code
in a Jupyter kernel and embed the output directly into your Sphinx documentation.

This extension adds at least one directive (see `sphinx_exec_jupyter.holoviews`_ for more):

..  rst:directive:: exec-jupyter

    Execute a Jupyter notebook cell and embed the output into the documentation.
    The Python expression on the last line of the directive body is displayed.

Examples
--------

.. code-block:: rst

    ..  exec-jupyter::

        import pandas as pd

        pd.DataFrame(dict(
            A=[1, 2, 3],
            B=[4, 5, 6],
        ))

results in:

..  exec-jupyter::

    import pandas as pd

    pd.DataFrame(dict(
        A=[1, 2, 3],
        B=[4, 5, 6],
    ))

``sphinx_exec_jupyter.holoviews``
---------------------------------

If you installed ``sphinx-exec-jupyter`` with the ``holoviews`` extra
(e.g. ``pip install sphinx-exec-jupyter[holoviews]``),
the ``sphinx_exec_jupyter.holoviews`` sub-extension is loaded automatically.

This extension adds a setting and one more directive:

..  confval:: holoviews_backends
    :type: ``list[str]``
    :default: ``['bokeh']``

    A list of backends to use for rendering HoloViews plots.

..  rst:directive:: holoviews

    Embed a HoloViews plot into the documentation.
    The Python expression on the last line of the directive body is displayed.

    ..  rst:directive:option:: backends: backend1,backend2,...
        :type: comma separated list of backends

        The list of backends to use for rendering the plot. Defaults to :confval:`holoviews_backends`.

..
    See here for syntax:
    https://www.sphinx-doc.org/en/master/usage/domains/restructuredtext.html#directive-rst-directive

.. _holoviews-examples:

Examples
--------

No options (defaults to bokeh):

.. code-block:: rst

    ..  holoviews::

        hv.Curve([1, 2, 3, 2, 1])

results in:

..  holoviews::

    hv.Curve([1, 2, 3, 2, 1])

With multiple backends specified (needs the ``sphinx_design`` extension to be loaded):

.. code-block:: rst

    ..  holoviews::
        :backends: bokeh,matplotlib,plotly

        hv.Curve([1, 2, 3, 2, 1])

results in:

..  holoviews::
    :backends: bokeh,matplotlib,plotly

    hv.Curve([1, 2, 3, 2, 1])
