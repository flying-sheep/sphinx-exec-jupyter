# SPDX-License-Identifier: MPL-2.0
"""Sphinx extension to run code snippets using Jupyter machinery."""

from __future__ import annotations

from contextlib import suppress
from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.errors import ExtensionError
from sphinx.util.typing import ExtensionMetadata

from ._directive import ExecJupyterDirective
from ._kernel_mgr import maybe_patch_myst_nb

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config


__all__ = ["ExecJupyterDirective", "setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Add directive(s) and settings to Sphinx."""
    app.setup_extension("myst_nb")
    app.add_config_value("exec_jupyter_code", "", "env")
    app.add_config_value("exec_jupyter_kernel", "python3", "env")
    app.add_config_value("exec_jupyter_patch_myst_nb", True, "env")  # noqa: FBT003
    app.add_directive("exec-jupyter", ExecJupyterDirective)
    app.connect("config-inited", _maybe_patch_myst_nb)

    with suppress(ExtensionError):
        app.setup_extension("sphinx_exec_jupyter.holoviews")

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )


def _maybe_patch_myst_nb(app: Sphinx, config: Config) -> None:
    ctx = maybe_patch_myst_nb(config)
    ctx.__enter__()

    def cleanup(app: Sphinx, exc: Exception | None) -> None:  # noqa: ARG001
        if exc is None:
            ctx.__exit__(None, None, None)
        else:
            ctx.__exit__(type(exc), exc, exc.__traceback__)

    app.connect("build-finished", cleanup)


def __getattr__(name: str) -> object:
    if name == "HoloViewsMimeRenderer":
        # Create dummy so `myst_nb.mime_renderers` entry point still resolves
        try:
            from .holoviews import HoloViewsMimeRenderer  # noqa: PLC0415
        except ImportError:
            from myst_nb.core.render import MimeRenderPlugin  # noqa: PLC0415

            class HoloViewsMimeRenderer(MimeRenderPlugin):
                pass

        return HoloViewsMimeRenderer

    raise AttributeError
