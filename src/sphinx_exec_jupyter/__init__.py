# SPDX-License-Identifier: MPL-2.0
"""Sphinx extension to run code snippets using Jupyter machinery."""

from __future__ import annotations

from contextlib import suppress
from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.errors import ExtensionError
from sphinx.util.typing import ExtensionMetadata

from ._directive import ExecJupyterDirective
from ._myst_patch import maybe_patch_myst_nb
from ._pending import PendingExecNode
from ._resolve import ExecPendingNodes

if TYPE_CHECKING:
    from sphinx.application import Sphinx


__all__ = ["ExecJupyterDirective", "setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Add directive(s) and settings to Sphinx."""
    app.setup_extension("myst_nb")
    app.add_config_value("exec_jupyter_code", "", "env")
    app.add_config_value("exec_jupyter_kernel", "python3", "env")
    app.add_config_value("exec_jupyter_isolate_per_document", True, "env")  # noqa: FBT003
    app.add_config_value("exec_jupyter_patch_myst_nb", False, "env")  # noqa: FBT003
    app.add_directive("exec-jupyter", ExecJupyterDirective)
    app.add_node(PendingExecNode)
    app.add_transform(ExecPendingNodes)
    app.connect("config-inited", maybe_patch_myst_nb)

    with suppress(ExtensionError):
        app.setup_extension("sphinx_exec_jupyter.holoviews")

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
