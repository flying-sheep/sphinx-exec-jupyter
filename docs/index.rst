sphinx-holoviews
================

This extension adds one directive:

..  rst:directive:: holoviews

    Embed a HoloViews plot into the documentation.
    The Python expression on the last line of the directive body is displayed.

    ..  rst:directive:option:: backends: backend1,backend2,...
        :type: comma separated list of backends

        The list of backends to use for rendering the plot. Defaults to ``bokeh``.

..
    See here for syntax:
    https://www.sphinx-doc.org/en/master/usage/domains/restructuredtext.html#directive-rst-directive

Examples
--------

No options (defaults to bokeh):

.. code-block:: rst

    ..  holoviews::

        hv.Curve([1, 2, 3, 2, 1])

results in:

..  holoviews::

    hv.Curve([1, 2, 3, 2, 1])

With multiple backends specified:

.. code-block:: rst

    ..  holoviews::
        :backends: bokeh,matplotlib,plotly

        hv.Curve([1, 2, 3, 2, 1])

results in:

..  holoviews::
    :backends: bokeh,matplotlib,plotly

    hv.Curve([1, 2, 3, 2, 1])
