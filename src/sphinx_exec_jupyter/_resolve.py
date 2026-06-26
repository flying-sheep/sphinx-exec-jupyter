# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from contextlib import suppress
from itertools import islice
from typing import TYPE_CHECKING, cast

from ._kernel_mgr import maybe_patch_myst_nb
from ._pending import PendingExecNode
from .common import execute_cells

with suppress(ImportError):
    from .holoviews._directive import hv_preload, process_hv_results

if TYPE_CHECKING:
    from docutils import nodes
    from myst_nb.sphinx_ import SphinxEnvType
    from sphinx.application import Sphinx


def exec_per_document(app: Sphinx, doctree: nodes.document) -> None:
    pending: list[PendingExecNode] = list(doctree.findall(PendingExecNode))
    if not pending:
        return

    if hv_backends := {
        backend for node in pending for backend in node["hv_backends"] or ()
    }:
        code = hv_preload(hv_backends, app.config.exec_jupyter_code)
    else:
        code = None

    all_cells = [c for node in pending for c in node["cells"]]
    with maybe_patch_myst_nb(app.config, code=code):
        all_results = execute_cells(all_cells, doctree)

    env = cast("SphinxEnvType", app.env)
    it = iter(all_results)
    for node in pending:
        results = list(islice(it, len(node["cells"])))
        if node["hv_backends"] is not None:
            results = process_hv_results(results, node["hv_backends"], env)
        node.replace_self(results)
