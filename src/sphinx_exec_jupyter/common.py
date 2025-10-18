# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import myst_nb.docutils_
import myst_nb.sphinx_ext
from nbformat import v4

if TYPE_CHECKING:
    from docutils import nodes


def execute_cells(cells: list[str], document: nodes.document) -> list[nodes.Node]:
    """Execute code cells and return resulting docutils nodes, one per cell."""
    notebook_json = json.dumps(
        v4.new_notebook(cells=[v4.new_code_cell(cell) for cell in cells])
    )
    document.settings.nb_execution_mode = "force"

    parser = myst_nb.docutils_.Parser()
    after_last_child = len(document.children)
    parser.parse(notebook_json, document)
    nodes = document.children[after_last_child:]
    del document.children[after_last_child:]
    return nodes
