# SPDX-License-Identifier: MPL-2.0

from sphinx_exec_jupyter._kernel_mgr import start_new_async_kernel


async def test_launch() -> None:
    km, kc = await start_new_async_kernel("foo = 1")
    resp = await kc.execute("foo", reply=True, timeout=0.200)
    assert resp == 1
