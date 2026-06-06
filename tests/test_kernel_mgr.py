# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from jupyter_client.asynchronous.client import AsyncKernelClient

    from sphinx_exec_jupyter._kernel_mgr import ForkingKernelManager


class StartKernel(Protocol):
    async def __call__(
        self, code: str, **kwargs
    ) -> tuple[ForkingKernelManager, AsyncKernelClient]: ...


@pytest.fixture
async def start_kernel() -> AsyncGenerator[StartKernel]:
    from sphinx_exec_jupyter._kernel_mgr import start_new_fork_kernel

    mgrs: list[tuple[ForkingKernelManager, AsyncKernelClient]] = []

    async def fn(code: str, **kwargs):
        km, kc = await start_new_fork_kernel(code, **kwargs)
        mgrs.append((km, kc))
        return km, kc

    try:
        yield fn
    finally:
        for km, kc in mgrs:
            kc.stop_channels()
            # km.shutdown_kernel takes a long time
            await km.provisioner.terminate()


@pytest.mark.parametrize(
    ("preload", "code", "resp_str"),
    [
        pytest.param("foo = 1", "foo", "1", id="assign"),
        pytest.param("import builtins", "builtins.__IPYTHON__", "True", id="enhance"),
    ],
)
async def test_launch(
    start_kernel: StartKernel, preload: str, code: str, resp_str: str
) -> None:
    km, kc = await start_kernel(preload)
    outputs = []

    resp = await kc.execute_interactive(code, output_hook=outputs.append, timeout=0.2)

    assert resp["msg_type"] == "execute_reply"
    assert resp["content"]["status"] == "ok"
    [result] = (output for output in outputs if output["msg_type"] == "execute_result")
    assert result["content"]["data"]["text/plain"] == resp_str
