# SPDX-License-Identifier: MPL-2.0
from typing import TYPE_CHECKING, cast

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from .common import execute_cells

if TYPE_CHECKING:
    from myst_nb.sphinx_ import SphinxEnvType

__all__ = ["ExecJupyterDirective"]


class ExecJupyterDirective(SphinxDirective):
    has_content = True

    def run(self) -> list[nodes.Node]:
        code = "\n".join(self.content)
        return execute_cells(
            [code], self.state.document, env=cast("SphinxEnvType", self.env)
        )
