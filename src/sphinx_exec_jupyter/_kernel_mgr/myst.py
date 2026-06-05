# SPDX-License-Identifier: MPL-2.0

from contextlib import contextmanager
from functools import partial

from jupyter_cache.executors.utils import single_nb_execution
from myst_nb.core.execute import cache, direct, inline

ModifiedNotebookClient = inline.ModifiedNotebookClient


@contextmanager
def patch_myst_nb(code: str):
    from . import ForkingKernelManager

    km = ForkingKernelManager(code)

    cache.single_nb_execution = partial(single_nb_execution, km=km)
    direct.single_nb_execution = partial(single_nb_execution, km=km)
    inline.ModifiedNotebookClient = partial(ModifiedNotebookClient, km=km)

    try:
        yield
    finally:
        cache.single_nb_execution = single_nb_execution
        direct.single_nb_execution = single_nb_execution
        inline.ModifiedNotebookClient = ModifiedNotebookClient
