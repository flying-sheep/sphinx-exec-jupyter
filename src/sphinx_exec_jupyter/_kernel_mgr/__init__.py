# SPDX-License-Identifier: MPL-2.0
"""Kernel manager for Jupyter kernels started from forked processes."""

from __future__ import annotations

import importlib.resources
import json
import os
import signal
from asyncio.subprocess import PIPE, create_subprocess_exec
from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast, overload, override

from jupyter_client import LocalPortCache
from jupyter_client.kernelspec import KernelSpec, KernelSpecManager
from jupyter_client.manager import AsyncKernelManager
from jupyter_client.provisioning.local_provisioner import LocalProvisioner
from jupyter_client.provisioning.provisioner_base import KernelProvisionerBase
from traitlets import Instance, default

from .myst import maybe_patch_myst_nb, patch_myst_nb

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Sequence
    from typing import Literal

    from jupyter_client import KernelConnectionInfo
    from traitlets import Unicode


__all__ = [
    "Cmd",
    "ForkingKernelManager",
    "maybe_patch_myst_nb",
    "patch_myst_nb",
    "start_new_fork_kernel",
]


class ForkCmd(TypedDict):
    cmd: Literal["fork"]
    argv: Sequence[str]


class ForkResp(TypedDict):
    pid: int


class WaitExitCmd(TypedDict):
    cmd: Literal["wait"]
    pid: int


class WaitExitResp(TypedDict):
    code: int


class ExitCodeCmd(TypedDict):
    cmd: Literal["exit_code"]
    pid: int


class ExitCodeResp(TypedDict):
    code: int | None


type Cmd = ForkCmd | WaitExitCmd | ExitCodeCmd
type Resp = ForkResp | WaitExitResp | ExitCodeResp


RUN_SERVER_CODE = (importlib.resources.files(__name__) / "fork-server.py").read_text()


@dataclass
class KernelForkServer:
    """A server that executes code and allows forking off kernels after."""

    py_cmd: tuple[str, ...]
    code: str
    process: Process | None = field(init=False, default=None)

    async def fork(self, cmd: Sequence[str]) -> int:
        if self.process is None:
            code = RUN_SERVER_CODE.replace('"USER_CODE_INSERTION_POINT"', self.code)
            self.process = await create_subprocess_exec(
                *self.py_cmd, "-c", code, stdin=PIPE, stdout=PIPE, stderr=PIPE
            )

        resp = await self._send_cmd(ForkCmd(cmd="fork", argv=cmd))
        return resp["pid"]

    async def get_exit_code(self, pid: int) -> int | None:
        if self.process is None:
            return None
        resp = await self._send_cmd(ExitCodeCmd(cmd="exit_code", pid=pid))
        return resp["code"]

    async def wait(self, pid: int) -> int:
        resp = await self._send_cmd(WaitExitCmd(cmd="wait", pid=pid))
        return resp["code"]

    @overload
    async def _send_cmd(self, cmd: ForkCmd) -> ForkResp: ...
    @overload
    async def _send_cmd(self, cmd: WaitExitCmd) -> WaitExitResp: ...
    @overload
    async def _send_cmd(self, cmd: ExitCodeCmd) -> ExitCodeResp: ...
    async def _send_cmd(self, cmd: Cmd) -> Resp:
        assert self.process and self.process.stdin and self.process.stdout
        self.process.stdin.write(json.dumps(cmd).encode("utf-8") + b"\n")
        await self.process.stdin.drain()
        if self.process.returncode is not None:
            assert self.process.stderr
            code = (
                signal.strsignal(-self.process.returncode)
                if self.process.returncode < 0
                else self.process.returncode
            )
            stderr = await self.process.stderr.read()
            msg = f"Server died ({code=}): {stderr.decode('utf-8').strip()}"
            raise RuntimeError(msg)
        return json.loads(await self.process.stdout.readline())


@dataclass
class ForkingProvisioner(KernelProvisionerBase):
    _: KW_ONLY

    # factory API
    kernel_id: Unicode | str
    kernel_spec: KernelSpec | None
    parent: ForkingKernelManager

    # internal state
    ports_cached: bool = field(init=False, default=False)
    server: KernelForkServer | None = field(init=False, default=None)
    pid: int | None = field(init=False, default=None)

    SERVERS: ClassVar[dict[tuple[tuple[str, ...], str], KernelForkServer]] = {}

    @property
    def code(self) -> str:
        return self.parent.code

    @property
    @override
    def has_process(self) -> bool:
        return self.pid is not None

    @override
    async def poll(self) -> int | None:  # `None` if running
        if self.pid is None or not self.server:
            return 0
        code = await self.server.get_exit_code(self.pid)
        if code is not None:
            self.pid = None
        return code

    @override
    async def wait(self) -> int | None:
        if self.pid is None or not self.server:
            return 0
        code = await self.server.wait(self.pid)
        self.pid = None
        return code

    @override
    async def send_signal(self, signum: int) -> None:
        assert self.pid
        os.kill(self.pid, signum)

    @override
    async def kill(self, restart: bool = False) -> None:
        assert self.pid
        os.kill(self.pid, signal.SIGKILL)

    @override
    async def terminate(self, restart: bool = False) -> None:
        assert self.pid
        os.kill(self.pid, signal.SIGTERM)

    @override
    async def launch_kernel(
        self, cmd: list[str], **kwargs: object
    ) -> KernelConnectionInfo:
        cls = type(self)
        m_idx = cmd.index("-m")
        py_cmd, kernel_argv = tuple(cmd[:m_idx]), cmd[m_idx + 2 :]
        self.server = cls.SERVERS.setdefault(
            (py_cmd, self.code), KernelForkServer(py_cmd, self.code)
        )
        self.pid = await self.server.fork(kernel_argv)
        return self.connection_info

    @override
    async def cleanup(self, restart: bool = False) -> None:
        await LocalProvisioner.cleanup(cast("LocalProvisioner", self), restart=restart)

    @override
    async def pre_launch(
        self, *, extra_arguments: Sequence[str] = (), **kwargs: object
    ) -> dict[str, object]:
        """Prepare for the kernel launch.

        Done in a way that’s basically copied from LocalKernelProvisioner,
        but we can’t just use that like `cleanup` above because it calls `super()`.
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
    """A KernelSpec that defaults to a forking provisioner."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.metadata.setdefault(
            "kernel_provisioner", dict(provisioner_name="forking_provisioner")
        )


class ForkingKernelSpecManager(KernelSpecManager):
    kernel_spec_class = ForkingKernelSpec


class ForkingKernelManager(AsyncKernelManager):
    """A KernelManager that starts kernels from forked processes.

    Parameters
    ----------
    code
        Code to execute before forking off a kernel.

    """

    kernel_spec_manager = Instance(ForkingKernelSpecManager)

    @default("kernel_spec_manager")
    def _default_kernel_spec_manager(self) -> ForkingKernelSpecManager:
        return ForkingKernelSpecManager(parent=self)

    code: str
    provisioner: ForkingProvisioner

    def __init__(self, code: str, **kw: object) -> None:
        super().__init__(**kw)
        self.code = code
