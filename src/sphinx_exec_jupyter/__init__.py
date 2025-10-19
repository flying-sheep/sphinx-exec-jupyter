# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

import myst_nb.sphinx_ext
from sphinx.errors import ExtensionError
from sphinx.util.typing import ExtensionMetadata

from ._directive import ExecJupyterDirective

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup", "ExecJupyterDirective"]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_directive("exec-jupyter", ExecJupyterDirective)

    try:
        app.setup_extension("sphinx_exec_jupyter.holoviews")
    except ExtensionError:
        pass

    if "myst_nb" not in app.extensions:
        myst_nb.sphinx_ext.add_css(app)
        app.connect("config-inited", myst_nb.sphinx_ext.add_exclude_patterns)
        app.connect("build-finished", myst_nb.sphinx_ext.add_global_html_resources)
        app.connect("html-page-context", myst_nb.sphinx_ext.add_per_page_html_resources)

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
