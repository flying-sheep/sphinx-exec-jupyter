# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from contextlib import suppress
from itertools import islice
from typing import TYPE_CHECKING, cast, override

from sphinx.transforms import SphinxTransform

from ._pending import PendingExecNode
from .common import execute_cells

with suppress(ImportError):
    from .holoviews._directive import hv_preload, process_hv_results

if TYPE_CHECKING:
    from myst_nb.sphinx_ import SphinxEnvType


class ExecPendingNodes(SphinxTransform):
    """Replace PendingExecNode placeholders with executed notebook output nodes."""

    default_priority = 500

    @override
    def apply(self, **_: object) -> None:
        pending: list[PendingExecNode] = list(self.document.findall(PendingExecNode))
        if not pending:
            return

        if hv_backends := {
            backend for node in pending for backend in node["hv_backends"] or ()
        }:
            code = hv_preload(hv_backends, self.config.exec_jupyter_code)
        else:
            code = None

        all_cells = [c for node in pending for c in node["cells"]]
        all_results = execute_cells(
            all_cells,
            self.document,
            kernel_name=self.config.exec_jupyter_kernel,
            prefix=code or self.config.exec_jupyter_code,
        )

        env = cast("SphinxEnvType", self.env)
        it = iter(all_results)
        for node in pending:
            results = list(islice(it, len(node["cells"])))
            if node["hv_backends"] is not None:
                results = process_hv_results(results, node["hv_backends"], env)
            node.replace_self(results)
