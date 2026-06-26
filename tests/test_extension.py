# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from importlib.util import find_spec
from itertools import product
from typing import TYPE_CHECKING

import pytest
from sphinx.testing.util import SphinxTestApp

if TYPE_CHECKING:
    from pathlib import Path

SKIP_NO_HV = pytest.mark.skipif(
    find_spec("holoviews") is None, reason="holoviews not installed"
)


def test_exec_jupyter_directive(tmp_path: Path) -> None:
    rst = """\
Test
====

.. exec-jupyter::

   print('exec_jupyter works')
"""
    (tmp_path / "conf.py").write_text('extensions = ["sphinx_exec_jupyter"]\n')
    (tmp_path / "index.rst").write_text(rst)
    app = SphinxTestApp("html", srcdir=tmp_path)
    try:
        app.build()
        html = (app.outdir / "index.html").read_text()
        assert "exec_jupyter works" in html
    finally:
        app.cleanup()


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(
            *(first, second),
            id=f"{first}-{second}",
            marks=SKIP_NO_HV if "holoviews" in (first, second) else (),
        )
        for first, second in product(("exec-jupyter", "holoviews"), repeat=2)
    ],
)
def test_shared_kernel(tmp_path: Path, first: str, second: str) -> None:
    any_hv = "holoviews" in (first, second)
    rst = f"""\
Test
====

..  {first}::

    x = 42

..  {second}::

    print(x)
    {"print(hv.__name__)" if any_hv else ""}
"""

    (tmp_path / "conf.py").write_text('extensions = ["sphinx_exec_jupyter"]\n')
    (tmp_path / "index.rst").write_text(rst)
    app = SphinxTestApp("html", srcdir=tmp_path)
    try:
        app.build()
        html = (app.outdir / "index.html").read_text()
        assert "42" in html
        if any_hv:
            assert "holoviews" in html
    finally:
        app.cleanup()
