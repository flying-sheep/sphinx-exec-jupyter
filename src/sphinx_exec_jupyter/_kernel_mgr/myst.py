# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING

import nbclient

if TYPE_CHECKING:
    from jupyter_client.manager import KernelManager
    from nbformat import NotebookNode

    from sphinx_exec_jupyter._kernel_mgr import ForkingKernelManager


KM_CACHE: dict[str, ForkingKernelManager] = {}


def get_km(code: str) -> ForkingKernelManager:
    if code not in KM_CACHE:
        from . import ForkingKernelManager

        KM_CACHE[code] = ForkingKernelManager(code)
    return KM_CACHE[code]


def execute(
    nb: NotebookNode,
    cwd: str | None = None,
    km: KernelManager | None = None,
    **kwargs: object,
) -> NotebookNode:
    """Execute notebook.

    Identical to the patched version except for `cleanup_kc=True`.
    """
    resources = {}
    if cwd is not None:
        resources["metadata"] = {"path": cwd}
    return nbclient.NotebookClient(nb=nb, resources=resources, km=km, **kwargs).execute(
        cleanup_kc=True
    )


@contextmanager
def patch_myst_nb(code: str, *, kernel_name: str):
    import jupyter_cache.executors.utils

    km = get_km(code)

    jupyter_cache.executors.utils.executenb = partial(
        execute, km=km, kernel_name=kernel_name, shutdown_kernel="immediate"
    )

    try:
        yield
    finally:
        jupyter_cache.executors.utils.executenb = nbclient.execute
