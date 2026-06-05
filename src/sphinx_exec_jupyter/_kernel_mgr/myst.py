# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING

from jupyter_cache.executors.utils import single_nb_execution
from myst_nb.core.execute.inline import ModifiedNotebookClient

if TYPE_CHECKING:
    from sphinx_exec_jupyter._kernel_mgr import ForkingKernelManager


KM_CACHE: dict[str, ForkingKernelManager] = {}


def get_km(code: str) -> ForkingKernelManager:
    if code not in KM_CACHE:
        from . import ForkingKernelManager

        KM_CACHE[code] = ForkingKernelManager(code)
    return KM_CACHE[code]


def shutdown_kernels():
    async def shutdown():
        await asyncio.gather(*[km.provisioner.terminate() for km in KM_CACHE.values()])

    asyncio.run(shutdown())
    KM_CACHE.clear()


@contextmanager
def patch_myst_nb(code: str, *, kernel_name: str):
    from myst_nb.core.execute import cache, direct, inline

    km = get_km(code)

    cache.single_nb_execution = direct.single_nb_execution = partial(
        single_nb_execution, km=km, kernel_name=kernel_name
    )
    inline.ModifiedNotebookClient = partial(
        ModifiedNotebookClient, km=km, kernel_name=kernel_name
    )

    try:
        yield
    finally:
        cache.single_nb_execution = single_nb_execution
        direct.single_nb_execution = single_nb_execution
        inline.ModifiedNotebookClient = ModifiedNotebookClient
