# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import mkstemp
from typing import TYPE_CHECKING

import myst_nb.sphinx_
from nbformat import v4

if TYPE_CHECKING:
    from collections.abc import Generator

    from docutils import nodes
    from myst_nb.sphinx_ import SphinxEnvType


def execute_cells(
    cells: list[str], document: nodes.document, *, env: SphinxEnvType
) -> list[nodes.Node]:
    """Execute code cells and return resulting docutils nodes, one per cell."""
    notebook_json = v4.writes(
        v4.new_notebook(cells=[v4.new_code_cell(cell) for cell in cells])
    )

    # execute notebook and append resulting nodes to document
    parser = myst_nb.sphinx_.Parser()
    parser.env = env
    after_last_child = len(document.children)
    with (
        temp_setting(parser.env.mystnb_config, "execution_mode", "force"),
        temp_setting(parser.env.mystnb_config, "execution_raise_on_error", True),
        temp_source_code(parser.env, notebook_json),
    ):
        parser.parse(notebook_json, document)

    # extract nodes and restore document
    nodes = document.children[after_last_child:]
    del document.children[after_last_child:]
    for key in ["words", "minutes"]:
        document.substitution_names.pop(f"wordcount-{key}", None)
        document.substitution_defs.pop(f"wordcount-{key}", None)

    return nodes


_unset = object()


@contextmanager
def temp_setting(env: object, key: str, value: object) -> Generator[None, None, None]:
    """Context manager to temporarily set a document setting."""
    old_value = getattr(env, key, _unset)
    setattr(env, key, value)
    try:
        yield
    finally:
        if old_value is _unset:
            delattr(env, key)
        else:
            setattr(env, key, old_value)


@contextmanager
def temp_source_code(
    env: SphinxEnvType, source_code: str
) -> Generator[Path, None, None]:
    """Context manager to temporarily set the current document."""
    fd, _p = mkstemp(suffix=".ipynb", text=True)
    path = Path(_p)
    with open(fd, "w", encoding="utf-8") as f:
        f.write(source_code)

    docname_tmp = path.stem

    def doc2path(docname: str, base: bool = True) -> Path:
        if docname == docname_tmp:
            return Path(path)
        return doc2path_orig(docname, base=base)

    env.current_document.docname, old_docname = docname_tmp, env.docname
    env.doc2path, doc2path_orig = doc2path, env.doc2path
    try:
        yield path
    finally:
        env.current_document.docname = old_docname
        env.doc2path = doc2path_orig
        path.unlink()
