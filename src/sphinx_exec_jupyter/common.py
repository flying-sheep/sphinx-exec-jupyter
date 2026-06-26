# SPDX-License-Identifier: MPL-2.0
"""Common code for sphinx-exec-jupyter."""

from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, TypedDict, cast, override

import myst_nb.sphinx_
from nbformat import NotebookNode, v4

if TYPE_CHECKING:
    from collections.abc import Generator

    from docutils import nodes
    from myst_nb.sphinx_ import SphinxEnvType


class ExtData(TypedDict, total=False):
    """Document metadata added by us."""

    count: int


def execute_cells(cells: list[str], document: nodes.document) -> list[nodes.Node]:
    """Execute code cells and return resulting docutils nodes, one per cell."""
    notebook_json = v4.writes(
        v4.new_notebook(
            metadata=NotebookNode(language_info=NotebookNode(name="python")),
            cells=[v4.new_code_cell(cell) for cell in cells],
        )
    )

    # execute notebook and append resulting nodes to document
    parser = myst_nb.sphinx_.Parser()
    after_last_child = len(document.children)
    with temp_source_code(document, notebook_json):
        parser.parse(notebook_json, document)

    # extract nodes and restore document
    nodes = document.children[after_last_child:]
    del document.children[after_last_child:]
    for key in ["words", "minutes"]:
        document.substitution_names.pop(f"wordcount-{key}", None)
        document.substitution_defs.pop(f"wordcount-{key}", None)

    return nodes


@contextmanager
def temp_source_code(
    document: nodes.document, source_code: str
) -> Generator[Path, None, None]:
    """Context manager to temporarily set the current document."""
    env = cast("SphinxEnvType", document.settings.env)
    ext_data = cast(
        "ExtData", env.current_document.setdefault("sphinx_exec_jupyter", {})
    )
    ext_data["count"] = ext_data.get("count", 0) + 1
    old_docname = env.docname
    docname_tmp = f"{old_docname}-exec-{ext_data['count']}"

    d = Path(mkdtemp())
    path = d / f"{docname_tmp}.ipynb"
    path.parent.mkdir(parents=True, exist_ok=True)  # when docname contains slashes
    path.write_text(source_code)

    @override
    def doc2path(docname: str, base: bool = True) -> Path:
        if docname == docname_tmp:
            return path
        return doc2path_orig(docname, base=base)

    env.current_document.docname = docname_tmp
    env.doc2path, doc2path_orig = doc2path, env.doc2path
    old_source, document.current_source = document.current_source, str(path)
    try:
        yield path
    finally:
        env.current_document.docname = old_docname
        env.doc2path = doc2path_orig
        document.current_source = old_source
        shutil.rmtree(d)
