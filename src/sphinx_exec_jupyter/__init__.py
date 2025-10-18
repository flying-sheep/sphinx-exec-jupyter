# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

import myst_nb.sphinx_ext
from sphinx.errors import ExtensionError
from sphinx.util.typing import ExtensionMetadata

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    try:
        app.setup_extension("sphinx_exec_jupyter.holoviews")
    except ExtensionError:
        pass

    app.connect("config-inited", myst_nb.sphinx_ext.add_exclude_patterns)
    app.connect("build-finished", myst_nb.sphinx_ext.add_global_html_resources)
    app.connect("html-page-context", myst_nb.sphinx_ext.add_per_page_html_resources)

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
