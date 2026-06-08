# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import jupyter_cache.executors.utils as jce
import nbformat
import pytest

from sphinx_exec_jupyter._kernel_mgr import ForkingProvisioner, patch_myst_nb

if TYPE_CHECKING:
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

    assert prov.call_count == 1
    [code_cell] = node["cells"]
    assert code_cell["cell_type"] == "code"
    [result] = code_cell["outputs"]
    assert result["output_type"] == "execute_result"
    assert result["data"]["text/plain"] == resp_str


def test_shutdown(subtests: pytest.Subtests):
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print('hi')")])

    for attempt in range(3):
        with subtests.test(attempt=attempt), patch_myst_nb("", kernel_name="python3"):
            jce.executenb(nb)
