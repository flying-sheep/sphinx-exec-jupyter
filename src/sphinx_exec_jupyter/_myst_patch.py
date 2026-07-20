# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from functools import partial
from typing import TYPE_CHECKING

import jupyter_cache.executors.utils

from ._kernel_mgr import forking_km_class

if TYPE_CHECKING:
    from collections.abc import Generator

    from sphinx.application import Sphinx
    from sphinx.config import Config


__all__ = ["maybe_patch_myst_nb"]


def maybe_patch_myst_nb(app: Sphinx, config: Config) -> None:
    ctx = (
        patch_myst_nb(config.exec_jupyter_code)
        if config.exec_jupyter_patch_myst_nb and config.exec_jupyter_code
        else nullcontext()
    )
    ctx.__enter__()

    def cleanup(app: Sphinx, exc: Exception | None) -> None:  # noqa: ARG001
        if exc is None:
            ctx.__exit__(None, None, None)
        else:
            ctx.__exit__(type(exc), exc, exc.__traceback__)

    app.connect("build-finished", cleanup)


@contextmanager
def patch_myst_nb(code: str) -> Generator[None]:
    orig_executenb = jupyter_cache.executors.utils.executenb
    jupyter_cache.executors.utils.executenb = partial(
        orig_executenb, kernel_manager_class=forking_km_class(code)
    )

    try:
        yield
    finally:
        jupyter_cache.executors.utils.executenb = orig_executenb
