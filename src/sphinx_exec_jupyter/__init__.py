# SPDX-License-Identifier: MPL-2.0
"""Sphinx extension to run code snippets using Jupyter machinery."""

from __future__ import annotations

import contextlib
from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.errors import ExtensionError
from sphinx.util.typing import ExtensionMetadata

from ._directive import ExecJupyterDirective

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__all__ = ["ExecJupyterDirective", "setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Add directive(s) and settings to Sphinx."""
    app.setup_extension(extname="myst_nb")
    app.add_config_value("exec_jupyter_code", "", "env")
    app.add_config_value("exec_jupyter_kernel", "python3", "env")
    app.add_directive("exec-jupyter", ExecJupyterDirective)

    with contextlib.suppress(ExtensionError):
        app.setup_extension("sphinx_exec_jupyter.holoviews")

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
