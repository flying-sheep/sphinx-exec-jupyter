# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.util.typing import ExtensionMetadata

from ._directive import HoloViewsDirective, HoloViewsOptions
from ._mime_render import HoloViewsMimeRenderer

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup", "HoloViewsDirective", "HoloViewsOptions", "HoloViewsMimeRenderer"]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_directive("holoviews", HoloViewsDirective)
    app.add_config_value("holoviews_backends", ["bokeh"], "env", {list})

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
