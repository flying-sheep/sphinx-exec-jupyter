# SPDX-License-Identifier: MPL-2.0

from contextlib import contextmanager
from functools import cache, partial

from jupyter_cache.executors.utils import single_nb_execution
from jupyter_client.manager import KernelManager
from myst_nb.core.execute.inline import ModifiedNotebookClient


@cache
def get_km(code: str) -> KernelManager:
    from . import ForkingKernelManager

    return ForkingKernelManager(code)


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
