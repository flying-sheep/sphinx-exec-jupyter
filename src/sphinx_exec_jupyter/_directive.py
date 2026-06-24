# SPDX-License-Identifier: MPL-2.0

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from ._kernel_mgr import patch_myst_nb
from .common import execute_cells

__all__ = ["ExecJupyterDirective"]


class ExecJupyterDirective(SphinxDirective):
    has_content = True

    def run(self) -> list[nodes.Node]:
        code = "\n".join(self.content)
        with patch_myst_nb(
            self.config.exec_jupyter_code, kernel_name=self.config.exec_jupyter_kernel
        ):
            return execute_cells([code], self.state.document)
