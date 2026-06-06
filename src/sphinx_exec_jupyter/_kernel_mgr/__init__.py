# SPDX-License-Identifier: MPL-2.0
"""Kernel manager for Jupyter kernels started from forked processes."""

from __future__ import annotations

import asyncio
import importlib.resources
import json
import os
import signal
from asyncio.subprocess import PIPE, create_subprocess_exec
from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, ClassVar, cast

from jupyter_client import LocalPortCache
from jupyter_client.kernelspec import KernelSpec, KernelSpecManager
from jupyter_client.manager import AsyncKernelManager
from jupyter_client.provisioning.local_provisioner import LocalProvisioner
from jupyter_client.provisioning.provisioner_base import KernelProvisionerBase
from traitlets import Instance, default

from .myst import patch_myst_nb, shutdown_kernels

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Sequence

    from jupyter_client import KernelConnectionInfo
    from jupyter_client.asynchronous.client import AsyncKernelClient
    from traitlets import Unicode


__all__ = [
    "ForkingKernelManager",
    "start_new_async_kernel",
    "patch_myst_nb",
    "shutdown_kernels",
]


RUN_SERVER_CODE = importlib.resources.read_text(__name__, "fork_server.py")


@dataclass
class ForkServer:
    interpreter: str
    code: str
    process: Process | None = field(init=False, default=None)

    async def fork(self, cmd: Sequence[str]) -> int:
        if self.process is None:
            # print(f"launching fork server for {self.interpreter} and {self.code!r}")
            code = RUN_SERVER_CODE.replace('"USER_CODE_INSERTION_POINT"', self.code)
            self.process = await create_subprocess_exec(
                *(self.interpreter, "-c", code),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
            )
        else:
            assert self.interpreter == cmd[0]

        assert self.process.stdin and self.process.stdout and self.process.stderr
        self.process.stdin.write(json.dumps(cmd).encode("utf-8") + b"\n")
        await self.process.stdin.drain()
        resp = await self.process.stdout.readline()

        if self.process.returncode is not None:
            code = (
                signal.strsignal(-self.process.returncode)
                if self.process.returncode < 0
                else self.process.returncode
            )
            stderr = await self.process.stderr.read()
            raise RuntimeError(
                f"Server died ({code=}): {stderr.decode('utf-8').strip()}"
            )
        return int(resp.decode("utf-8").strip())


@dataclass
class ForkingKernelProvisioner(KernelProvisionerBase):
    _: KW_ONLY

    # factory API
    kernel_id: Unicode | str
    kernel_spec: KernelSpec | None
    parent: ForkingKernelManager

    # internal state
    ports_cached: bool = field(init=False, default=False)
    server: ForkServer | None = field(init=False, default=None)
    pid: int | None = field(init=False, default=None)

    SERVERS: ClassVar[dict[tuple[str, str], ForkServer]] = {}

    @property
    def code(self) -> str:
        return self.parent.code

    @property
    def has_process(self) -> bool:
        return self.pid is not None

    async def poll(self) -> int | None:
        assert self.pid
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return await self.wait()
        return None

    async def wait(self) -> int | None:
        assert self.pid
        _pid, status = await asyncio.to_thread(os.waitpid, self.pid, 0)
        return os.waitstatus_to_exitcode(status)

    async def send_signal(self, signum: int) -> None:
        assert self.pid
        os.kill(self.pid, signum)

    async def kill(self, restart: bool = False) -> None:
        assert self.pid
        os.kill(self.pid, signal.SIGKILL)

    async def terminate(self, restart: bool = False) -> None:
        assert self.pid
        os.kill(self.pid, signal.SIGTERM)

    async def launch_kernel(
        self, cmd: list[str], **kwargs: object
    ) -> KernelConnectionInfo:
        cls = type(self)
        self.server = cls.SERVERS.setdefault(
            (cmd[0], self.code), ForkServer(cmd[0], self.code)
        )
        self.pid = await self.server.fork(cmd)
        return self.connection_info

    async def cleanup(self, restart: bool = False) -> None:
        await LocalProvisioner.cleanup(cast("LocalProvisioner", self), restart=restart)

    async def pre_launch(
        self, *, extra_arguments: Sequence[str] = (), **kwargs: object
    ) -> dict[str, object]:
        """Prepare for the kernel launch in a way that’s basically copied from LocalKernelProvisioner.

        But we can’t just use that like `cleanup` above because it calls `super()`.
        """
        assert self.kernel_spec
        km = self.parent
        if km.cache_ports and not self.ports_cached:
            lpc = LocalPortCache.instance()
            km.shell_port = lpc.find_available_port(km.ip)
            km.iopub_port = lpc.find_available_port(km.ip)
            km.stdin_port = lpc.find_available_port(km.ip)
            km.hb_port = lpc.find_available_port(km.ip)
            km.control_port = lpc.find_available_port(km.ip)
            self.ports_cached = True
        if env := cast("dict[str, object] | None", kwargs.get("env")):
            jupyter_session = env.get("JPY_SESSION_NAME", "")
            km.write_connection_file(jupyter_session=jupyter_session)
        else:
            km.write_connection_file()
        self.connection_info = km.get_connection_info()
        kernel_cmd = km.format_kernel_cmd(extra_arguments=list(extra_arguments))
        return await super().pre_launch(cmd=kernel_cmd, **kwargs)


class ForkingKernelSpec(KernelSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata["kernel_provisioner"] = dict(
            provisioner_name="forking_provisioner"
        )


class ForkingKernelSpecManager(KernelSpecManager):
    kernel_spec_class = ForkingKernelSpec


class ForkingKernelManager(AsyncKernelManager):
    kernel_spec_manager = Instance(ForkingKernelSpecManager)

    @default("kernel_spec_manager")
    def _default_kernel_spec_manager(self):
        return ForkingKernelSpecManager(parent=self)

    code: str
    provisioner: ForkingKernelProvisioner

    def __init__(self, code: str, **kw):
        super().__init__(**kw)
        self.code = code


async def start_new_async_kernel(
    code: str,
    *,
    startup_timeout: float = 60,
    kernel_name: str = "python",
    **kwargs: object,
) -> tuple[ForkingKernelManager, AsyncKernelClient]:
    """Start a new kernel, and return its Manager and Client."""
    km = ForkingKernelManager(code, kernel_name=kernel_name)
    await km.start_kernel(**kwargs)
    kc = km.client()
    kc.start_channels()
    try:
        await kc.wait_for_ready(timeout=startup_timeout)
    except RuntimeError:
        kc.stop_channels()
        await km.shutdown_kernel()
        raise

    return km, kc
