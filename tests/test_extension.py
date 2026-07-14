# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from importlib.util import find_spec
from itertools import product
from typing import TYPE_CHECKING

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

if TYPE_CHECKING:
    from pathlib import Path

SKIP_NO_HV = pytest.mark.skipif(
    find_spec("holoviews") is None, reason="holoviews not installed"
)


def run(
    rst: str, tmp_path: Path, *, conf: dict[str, object] | None = None
) -> dict[str, dict[str, nodes.literal_block | nodes.image]]:
    (tmp_path / "conf.py").write_text('extensions = ["sphinx_exec_jupyter"]\n')
    (tmp_path / "index.rst").write_text(rst)
    app = SphinxTestApp("html", srcdir=tmp_path, confoverrides=conf)

    app.build()
    doc = app.env.get_doctree("index")
    app.cleanup()

    cells: dict[str, dict[str, nodes.literal_block | nodes.image]] = {}
    for cell in doc.findall(
        lambda n: isinstance(n, nodes.Element) and "cell" in n["classes"]
    ):
        assert isinstance(cell, nodes.container)
        code = cell.children[0].children[0].astext()
        if len(cell.children) == 1:
            cells[code] = {}
            continue

        [in_, cell_out] = cell.children
        assert isinstance(in_, nodes.container)
        assert isinstance(cell_out, nodes.container)
        assert len(cell_out.children) == 1, (
            f"expected single cell output, got {[c.pformat() for c in cell_out]}"
        )
        [output] = cell_out.children
        if output.attributes.get("nb_element", None) == "mime_bundle":
            cells[code] = {m["mime_type"]: m.children[0] for m in output.children}
        else:
            cells[code] = {"text/plain": output}

    return cells


def test_exec_jupyter_directive(tmp_path: Path) -> None:
    rst = """\
..  exec-jupyter::

    print('exec_jupyter works')
"""

    [out] = run(rst, tmp_path).values()

    assert out["text/plain"].astext() == "exec_jupyter works\n"


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param(
            *(first, second),
            id="-".join(p.replace("-", "_") for p in (first, second)),
            marks=SKIP_NO_HV if "holoviews" in (first, second) else (),
        )
        for first, second in product(("exec-jupyter", "holoviews"), repeat=2)
    ],
)
def test_shared_kernel(tmp_path: Path, first: str, second: str) -> None:
    any_hv = "holoviews" in (first, second)
    rst = f"""\
..  {first}::

    x = 42

..  {second}::

    print(x)
    {"print(hv.__name__)" if any_hv else ""}
"""

    _, out = run(rst, tmp_path).values()
    lines = out["text/plain"].astext().splitlines()

    assert lines[0] == "42"
    if any_hv:
        assert lines[1] == "holoviews"


@SKIP_NO_HV
def test_holoviews_fake_backend(tmp_path: Path) -> None:
    rst = """\
..  holoviews::

    print(FAKE_BACKEND)
"""

    [(code, out)] = run(rst, tmp_path).items()

    assert code == "print('bokeh')"
    assert out["text/plain"].astext() == "None\n"


def test_add_image_dimensions(tmp_path: Path) -> None:
    rst = """\
..  exec-jupyter::

    %matplotlib inline

    import matplotlib.pyplot as plt
    plt.plot([1, 2, 3]);
"""

    [out] = run(rst, tmp_path).values()

    assert "image/png" in out
    assert "width" in out["image/png"].attributes
    assert "height" in out["image/png"].attributes


def test_mpl_inline_after_warm_preload(tmp_path: Path) -> None:
    """`matplotlib_inline` registration triggered before forking must still
    apply to the real kernel, not just the (discarded) warm-up shell."""
    rst = """\
..  exec-jupyter::

    import matplotlib.pyplot as plt
    plt.plot([1, 2, 3]);
"""

    preload = (
        "import matplotlib\n"
        "matplotlib.use('module://matplotlib_inline.backend_inline')\n"
        "import matplotlib.pyplot as plt\n"
        "plt.figure()"
    )
    [out] = run(rst, tmp_path, conf=dict(exec_jupyter_code=preload)).values()

    assert "image/png" in out
