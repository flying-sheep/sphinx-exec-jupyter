# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from contextlib import contextmanager
from functools import partial

import nbclient
from jupyter_cache.executors.utils import executenb


@contextmanager
def patch_myst_nb(code: str, *, kernel_name: str):
    import jupyter_cache.executors.utils

    from . import ForkingKernelManager

    class F(ForkingKernelManager):
        def __init__(self, *args, **kwargs):
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
