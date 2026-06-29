``sphinx_exec_jupyter``
=======================

The ``sphinx-exec-jupyter`` Sphinx extension allows you to execute code
in a Jupyter kernel and embed the output directly into your Sphinx documentation.

This extension adds at least one directive (see `sphinx_exec_jupyter.holoviews`_ for more):

..  rst:directive:: exec-jupyter

    Execute a Jupyter notebook cell and embed the output into the documentation.
    The Python expression on the last line of the directive body is displayed.

It can be configured with the following settings:

.. confval:: exec_jupyter_code
    :type: ``str``

    Prefix code to execute before the code in ``exec-jupyter`` or ``holoviews``.
    Kernels are started from forked processes after this code is executed,
    so it can be used for long-running initialization code (e.g. slow imports).

.. confval:: exec_jupyter_kernel
    :type: ``str``

    Name of the Jupyter kernel to use.
    If not set, the default kernel is used.

.. confval:: exec_jupyter_isolate_per_document
    :type: ``bool``
    :default: ``True``

    If ``True``, all directives in the same document share a single kernel,
    so variables defined in one directive are accessible in later ones.
    When ``False``, each directive runs in its own isolated kernel.

.. confval:: exec_jupyter_patch_myst_nb
    :type: ``bool``
    :default: ``True``

    If ``True`` and either ``exec_jupyter_code`` or ``exec_jupyter_kernel`` are set,
    the ``myst_nb`` extension is patched to use the provided code and/or kernel.

Examples
--------

Just use it like a code block:

..  code-block:: rst

    ..  exec-jupyter::

        <code>

The code gets executed and you see both code and results:

..  exec-jupyter::

    import pandas as pd

    pd.DataFrame(dict(
        A=[1, 2, 3],
        B=[4, 5, 6],
    ))

If you use :confval:`exec_jupyter_code`,
you can’t use IPython magic commands in it.

The following example uses matplotlib ``%`` magics, which could be spelled as
``matplotlib.use('module://matplotlib_inline.backend_inline')`` and
``matplotlib_inline.backend_inline.set_matplotlib_formats('retina')`` in preload code.

..  exec-jupyter::

    %matplotlib inline
    %config InlineBackend.figure_format='retina'

    import matplotlib.pyplot as plt

    plt.figure(figsize=(4, 2))
    plt.plot([1, 2, 1]);

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
