# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from functools import partial
from typing import TYPE_CHECKING

import jupyter_cache.executors.utils

if TYPE_CHECKING:
    from collections.abc import Generator

    from sphinx.config import Config


__all__ = ["maybe_patch_myst_nb"]


@contextmanager
def maybe_patch_myst_nb(
    config: Config, *, code: str | None = None, is_local: bool = True
) -> Generator[None]:
    """Patch myst-nb if needed.

    if `is_local` is False, respect `config.exec_jupyter_patch_myst_nb`.
    """
    code = code or config.exec_jupyter_code
    do_patch = (is_local or config.exec_jupyter_patch_myst_nb) and code
    with patch_myst_nb(code) if do_patch else nullcontext():
        yield


@contextmanager
def patch_myst_nb(code: str) -> Generator[None]:
    from . import ForkingKernelManager  # noqa: PLC0415

    class F(ForkingKernelManager):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(code, *args, **kwargs)

    orig_executenb = jupyter_cache.executors.utils.executenb
    jupyter_cache.executors.utils.executenb = partial(
        orig_executenb, kernel_manager_class=F
    )

    try:
        yield
    finally:
        jupyter_cache.executors.utils.executenb = orig_executenb
