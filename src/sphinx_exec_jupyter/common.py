# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, TypedDict, cast

import myst_nb.sphinx_
from nbformat import v4

if TYPE_CHECKING:
    from collections.abc import Generator

    from docutils import nodes
    from myst_nb.sphinx_ import SphinxEnvType


class ExtData(TypedDict, total=False):
    count: int


def execute_cells(
    cells: list[str],
    document: nodes.document,
    *,
    env: SphinxEnvType,
) -> list[nodes.Node]:
    """Execute code cells and return resulting docutils nodes, one per cell."""
    notebook_json = v4.writes(
        v4.new_notebook(cells=[v4.new_code_cell(cell) for cell in cells])
    )

    # execute notebook and append resulting nodes to document
    parser = myst_nb.sphinx_.Parser()
    parser.env = env
    after_last_child = len(document.children)
    with temp_source_code(parser.env, notebook_json):
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
    env: SphinxEnvType, source_code: str
) -> Generator[Path, None, None]:
    """Context manager to temporarily set the current document."""
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

    def doc2path(docname: str, base: bool = True) -> Path:
        if docname == docname_tmp:
            return path
        return doc2path_orig(docname, base=base)

    env.current_document.docname = docname_tmp
    env.doc2path, doc2path_orig = doc2path, env.doc2path
    try:
        yield path
    finally:
        env.current_document.docname = old_docname
        env.doc2path = doc2path_orig
        shutil.rmtree(d)
