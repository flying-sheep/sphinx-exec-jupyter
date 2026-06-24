# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import jupyter_cache.executors.utils as jce
import nbformat
import pytest

from sphinx_exec_jupyter._kernel_mgr import ForkingProvisioner, patch_myst_nb

if TYPE_CHECKING:
    from pathlib import Path

    from nbformat_types.versions import current as nbt
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    ("preload", "code", "resp_str"),
    [
        pytest.param("foo = 1", "foo", "1", id="assign"),
        pytest.param("import builtins", "builtins.__IPYTHON__", "True", id="enhance"),
    ],
)
def test_patch(mocker: MockerFixture, preload: str, code: str, resp_str: str) -> None:
    prov = mocker.spy(ForkingProvisioner, "__init__")
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(code)])

    with patch_myst_nb(preload, kernel_name="python3"):
        node = cast("nbt.Document", jce.executenb(nb))

    assert prov.call_count == 1, "didn’t actually use our provisioner"
    [code_cell] = node["cells"]
    assert code_cell["cell_type"] == "code"
    [result] = code_cell["outputs"]
    assert result["output_type"] == "execute_result"
    assert result["data"]["text/plain"] == resp_str


def test_shutdown(subtests: pytest.Subtests) -> None:
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print('hi')")])

    for attempt in range(2):
        with subtests.test(attempt=attempt), patch_myst_nb("", kernel_name="python3"):
            jce.executenb(nb)


def test_caching() -> None:
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print('hi')")])

    sleep = timedelta(milliseconds=400)

    times: list[timedelta] = []
    for _attempt in range(3):
        start = datetime.now(tz=UTC)
        with patch_myst_nb(
            f"import time; time.sleep({sleep.total_seconds()})", kernel_name="python3"
        ):
            jce.executenb(nb)
        times.append(datetime.now(tz=UTC) - start)

    # the first attempt should be longer than subsequent ones
    # since it’s the one that sets up the interpreter and then sleeps
    assert times[0] >= times[1] + sleep
    assert times[0] >= times[2] + sleep


def test_python_interpreter_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Kernel specs that include Python interpreter flags must work."""
    kernelspec = dict(
        argv=[
            *(sys.executable, "-Xfrozen_modules=off", "-m"),
            *("ipykernel_launcher", "-f", "{connection_file}"),
        ],
        display_name="Python 3 (frozen modules off)",
        language="python",
    )
    kernel_dir = tmp_path / "kernels" / "python3-frozen"
    kernel_dir.mkdir(parents=True)
    (kernel_dir / "kernel.json").write_text(json.dumps(kernelspec))
    monkeypatch.setenv("JUPYTER_PATH", str(tmp_path))

    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("1 + 1")])
    with patch_myst_nb("", kernel_name="python3-frozen"):
        jce.executenb(nb)
