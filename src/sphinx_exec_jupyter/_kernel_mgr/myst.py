# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING

import jupyter_cache.executors.utils
import nbclient
from jupyter_cache.executors.utils import executenb

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def patch_myst_nb(code: str, *, kernel_name: str) -> Generator[None]:
    from . import ForkingKernelManager  # noqa: PLC0415

    class F(ForkingKernelManager):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(code, *args, **kwargs)

    jupyter_cache.executors.utils.executenb = partial(
        executenb,
        kernel_manager_class=F,
        kernel_name=kernel_name,
        shutdown_kernel="immediate",
    )

    try:
        yield
    finally:
        jupyter_cache.executors.utils.executenb = nbclient.execute
