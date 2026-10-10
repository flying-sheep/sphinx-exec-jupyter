# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.util.docutils import SphinxDirective

from ._pending import PendingExecNode
from .common import execute_cells

if TYPE_CHECKING:
    from docutils import nodes


__all__ = ["ExecJupyterDirective"]


class ExecJupyterDirective(SphinxDirective):
    has_content = True

    def run(self) -> list[nodes.Node]:
        code = "\n".join(self.content)
        if self.config.exec_jupyter_isolate_per_document:
            return [PendingExecNode(cells=[code], hv_backends=None)]
        kernel_name = self.config.exec_jupyter_kernel
        return execute_cells(
            [code],
            self.state.document,
            kernel_name=kernel_name,
            prefix=self.config.exec_jupyter_code,
        )
