# SPDX-License-Identifier: MPL-2.0
"""Holoviews sub-extension for sphinx-exec-jupyter."""

from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.util.typing import ExtensionMetadata

from ._directive import HoloViewsDirective, HoloViewsDirectiveOptions

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["HoloViewsDirective", "HoloViewsDirectiveOptions", "setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Add holoviews-specific directive and setting to Sphinx."""
    app.add_directive("holoviews", HoloViewsDirective)
    app.add_config_value("holoviews_backends", ["bokeh"], "env", {list})

    # `parallel_read_safe` is `False` because of a race condition in patching myst_nb
    # the other directive uses only one preload script per run so that’s fine.
    # See https://github.com/executablebooks/MyST-NB/issues/574
    # and https://github.com/executablebooks/MyST-NB/issues/643
    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=False,
        parallel_write_safe=True,
    )
