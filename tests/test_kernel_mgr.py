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
import pytest

from sphinx_exec_jupyter._kernel_mgr import (
    FORK_ENV_VAR,
    ForkingProvisioner,
    KernelForkServer,
    forking_km_class,
)
from sphinx_exec_jupyter._myst_patch import patch_myst_nb
from sphinx_exec_jupyter.common import _python_notebook

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from pathlib import Path

    from nbformat_types.versions import current as nbt
    from pytest_mock import MockerFixture

    from sphinx_exec_jupyter._kernel_mgr import Cmd, Resp


def execute(
    preload: str, code: str, *, patch: bool, kernel_name: str = "python3"
) -> nbt.Document:
    nb = _python_notebook([code], kernel_name)
    if patch:
        with patch_myst_nb(preload):
            node = jce.executenb(nb)
    else:
        node = jce.executenb(nb, kernel_manager_class=forking_km_class(preload))
    return cast("nbt.Document", node)


@pytest.fixture(scope="session", params=[True, False], ids=["patch", "no_patch"])
def patch(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.mark.parametrize(
    ("preload", "code", "resp_str"),
    [
        pytest.param("foo = 1", "foo", "1", id="assign"),
        pytest.param("import builtins", "builtins.__IPYTHON__", "True", id="enhance"),
    ],
)
def test_patch(
    *, mocker: MockerFixture, preload: str, code: str, resp_str: str, patch: bool
) -> None:
    prov = mocker.spy(ForkingProvisioner, "__init__")

    node = execute(preload, code, patch=patch)

    assert prov.call_count == 1, "didn’t actually use our provisioner"
    [code_cell] = node["cells"]
    assert code_cell["cell_type"] == "code"
    [result] = code_cell["outputs"]
    assert result["output_type"] == "execute_result"
    assert result["data"]["text/plain"] == resp_str


def test_no_fork_fallback(
    *, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, patch: bool
) -> None:
    """Without forking, kernels are exec-launched but still run the preload code."""
    monkeypatch.setenv(FORK_ENV_VAR, "0")
    prov = mocker.spy(ForkingProvisioner, "__init__")

    node = execute("foo = 1", "foo", patch=patch)

    assert prov.call_count == 0, "should not use the forking provisioner"
    [code_cell] = node["cells"]
    assert code_cell["cell_type"] == "code"
    [result] = code_cell["outputs"]
    assert result["output_type"] == "execute_result"
    assert result["data"]["text/plain"] == "1"


def test_shutdown(*, subtests: pytest.Subtests, patch: bool) -> None:
    for attempt in range(2):
        with subtests.test(attempt=attempt), patch_myst_nb(""):
            execute("", "print('hi')", patch=patch)


def test_caching(*, patch: bool) -> None:
    sleep = timedelta(milliseconds=400)
    # the trailing comment keeps `patch`/`no_patch` from sharing a warm
    # fork-server, which is cached by the exact preload string
    preload = f"import time; time.sleep({sleep.total_seconds()})  # {patch=}"

    times: list[timedelta] = []
    for _attempt in range(3):
        start = datetime.now(tz=UTC)
        execute(preload, "print('hi')", patch=patch)
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
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, patch: bool
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

    execute("", "1 + 1", patch=patch, kernel_name="python3-frozen")
