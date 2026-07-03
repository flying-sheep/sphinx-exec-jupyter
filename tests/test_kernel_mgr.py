# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import asyncio
import json
import sys
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import jupyter_cache.executors.utils as jce
import nbformat
import pytest

from sphinx_exec_jupyter._kernel_mgr import (
    FORK_ENV_VAR,
    ForkingProvisioner,
    KernelForkServer,
)
from sphinx_exec_jupyter._kernel_mgr.myst import patch_myst_nb
from sphinx_exec_jupyter.common import _python_notebook

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from pathlib import Path

    from nbformat_types.versions import current as nbt
    from pytest_mock import MockerFixture

    from sphinx_exec_jupyter._kernel_mgr import Cmd, Resp


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

    with patch_myst_nb(preload):
        node = cast("nbt.Document", jce.executenb(nb))

    assert prov.call_count == 1, "didn’t actually use our provisioner"
    [code_cell] = node["cells"]
    assert code_cell["cell_type"] == "code"
    [result] = code_cell["outputs"]
    assert result["output_type"] == "execute_result"
    assert result["data"]["text/plain"] == resp_str


def test_no_fork_fallback(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without forking, kernels are exec-launched but still run the preload code."""
    monkeypatch.setenv(FORK_ENV_VAR, "0")
    prov = mocker.spy(ForkingProvisioner, "__init__")
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("foo")])

    with patch_myst_nb("foo = 1"):
        node = cast("nbt.Document", jce.executenb(nb))

    assert prov.call_count == 0, "should not use the forking provisioner"
    [code_cell] = node["cells"]
    assert code_cell["cell_type"] == "code"
    [result] = code_cell["outputs"]
    assert result["output_type"] == "execute_result"
    assert result["data"]["text/plain"] == "1"


def test_shutdown(subtests: pytest.Subtests) -> None:
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print('hi')")])

    for attempt in range(2):
        with subtests.test(attempt=attempt), patch_myst_nb(""):
            jce.executenb(nb)


def test_caching() -> None:
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("print('hi')")])

    sleep = timedelta(milliseconds=400)

    times: list[timedelta] = []
    for _attempt in range(3):
        start = datetime.now(tz=UTC)
        with patch_myst_nb(f"import time; time.sleep({sleep.total_seconds()})"):
            jce.executenb(nb)
        times.append(datetime.now(tz=UTC) - start)

    # the first attempt should be longer than subsequent ones
    # since it’s the one that sets up the interpreter and then sleeps
    assert times[0] >= times[1] + sleep
    assert times[0] >= times[2] + sleep


async def test_fork_server_concurrent_calls_dont_cross_talk() -> None:
    """Concurrent `fork`/`wait` calls on a shared `KernelForkServer` must not read
    each other’s replies off the pipe.

    The fake server below always replies in the order it received commands,
    exactly like the real one (`fork-server.py`) does.
    It replies to `fork` slower than to `wait`, so we trigger a race condition:
    Without lock, `fork()`→`wait()` results in switched replies,
    i.e. a `fork()` reads back `{"code": ...}` and crashes with `KeyError: 'pid'`.
    """
    cmd_queue: asyncio.Queue[Cmd] = asyncio.Queue()
    resp_queue: asyncio.Queue[Resp] = asyncio.Queue()
    last_cmd: str | None = None

    class FakeStdin:
        def write(self, data: bytes) -> None:
            nonlocal last_cmd
            msg = json.loads(data)
            last_cmd = msg["cmd"]
            cmd_queue.put_nowait(msg)

        async def drain(self) -> None:
            if last_cmd == "fork":  # simulate `os.fork()` taking a moment
                await asyncio.sleep(0.05)

    class FakeStdout:
        async def readline(self) -> bytes:
            resp = await resp_queue.get()
            return (json.dumps(resp) + "\n").encode()

    async def fake_fork_server() -> None:
        next_pid = 1
        while True:
            cmd = await cmd_queue.get()
            if cmd["cmd"] == "fork":
                await resp_queue.put({"pid": next_pid})
                next_pid += 1
            else:
                await resp_queue.put({"code": 0})

    server = KernelForkServer(py_cmd=(), code="")
    fake_process = SimpleNamespace(
        stdin=FakeStdin(), stdout=FakeStdout(), stderr=None, returncode=None
    )
    server.process = cast("Process", fake_process)
    server_task = asyncio.create_task(fake_fork_server())
    try:
        fork_task = asyncio.create_task(server.fork(["ignored"], "log.txt"))
        wait_task = asyncio.create_task(server.wait(123))
        results = await asyncio.gather(fork_task, wait_task, return_exceptions=True)
        assert results == [1, 0]
    finally:
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task


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

    nb = _python_notebook(["1 + 1"], "python3-frozen")
    with patch_myst_nb(""):
        jce.executenb(nb)
