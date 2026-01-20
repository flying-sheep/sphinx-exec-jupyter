# SPDX-License-Identifier: MPL-2.0

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from .common import execute_cells

__all__ = ["ExecJupyterDirective"]


class ExecJupyterDirective(SphinxDirective):
    has_content = True

    def run(self) -> list[nodes.Node]:
        code = "\n".join(self.content)
        return execute_cells([code], self.state.document)
