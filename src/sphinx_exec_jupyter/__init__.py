# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.errors import ExtensionError
from sphinx.util.typing import ExtensionMetadata

from ._directive import ExecJupyterDirective

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["setup", "ExecJupyterDirective"]


def setup(app: Sphinx) -> ExtensionMetadata:
    app.setup_extension(extname="myst_nb")
    app.add_directive("exec-jupyter", ExecJupyterDirective)

    try:
        app.setup_extension("sphinx_exec_jupyter.holoviews")
    except ExtensionError:
        pass

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
