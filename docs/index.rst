sphinx-holoviews
================

This extension adds one directive:

..  rst:directive:: holoviews

    Embed a HoloViews plot into the documentation.

    ..  rst:directive:option:: backends: backend1,backend2,...
        :type: comma separated list of backends

        The list of backends to use for rendering the plot. Defaults to ``bokeh``.

..
    See here for syntax:
    https://www.sphinx-doc.org/en/master/usage/domains/restructuredtext.html#directive-rst-directive

Examples
--------

No options (defaults to bokeh):

..  holoviews::

    hv.Curve([1, 2, 3, 2, 1])

With ``:backends: bokeh,matplotlib,plotly``:

..  holoviews::
    :backends: bokeh,matplotlib,plotly

    hv.Curve([1, 2, 3, 2, 1])
