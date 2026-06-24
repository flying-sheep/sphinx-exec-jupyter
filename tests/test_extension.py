# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.testing.util import SphinxTestApp

if TYPE_CHECKING:
    from pathlib import Path


def test_exec_jupyter_directive(tmp_path: Path) -> None:
    (tmp_path / "conf.py").write_text('extensions = ["sphinx_exec_jupyter"]\n')
    (tmp_path / "index.rst").write_text(
        "Test\n====\n\n.. exec-jupyter::\n\n   print('exec_jupyter works')\n"
    )
    app = SphinxTestApp("html", srcdir=tmp_path)
    try:
        app.build()
        html = (app.outdir / "index.html").read_text()
        assert "exec_jupyter works" in html
    finally:
        app.cleanup()
