# SPDX-License-Identifier: MPL-2.0
"""Kernel manager for Jupyter kernels started from forked processes."""

from __future__ import annotations

import importlib.resources
import json
import os
import signal
import sys
import tempfile
from asyncio import Lock
from asyncio.subprocess import PIPE, create_subprocess_exec
from contextlib import ExitStack, suppress
from dataclasses import KW_ONLY, dataclass, field
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast, overload, override

from jupyter_client import LocalPortCache
from jupyter_client.kernelspec import KernelSpec, KernelSpecManager
from jupyter_client.manager import AsyncKernelManager
from jupyter_client.provisioning.local_provisioner import LocalProvisioner
from jupyter_client.provisioning.provisioner_base import KernelProvisionerBase
from traitlets import Instance, default

if TYPE_CHECKING:
    from asyncio.subprocess import Process
    from collections.abc import Awaitable, Callable, Sequence
    from typing import Concatenate, Literal

    from jupyter_client import KernelConnectionInfo
    from traitlets import Unicode


__all__ = [
    "FORK_ENV_VAR",
    "Cmd",
    "ForkingKernelManager",
    "Resp",
    "forking_km_class",
    "forking_supported",
    "start_new_fork_kernel",
]


FILES = importlib.resources.files(__name__)


#: Environment variable to force-enable (``1``) or force-disable (``0``) the
#: forking provisioner, overriding the platform default.
FORK_ENV_VAR = "SPHINX_EXEC_JUPYTER_FORK"


def forking_supported() -> bool:
    """Whether forking a warm interpreter into kernels is safe on this platform.

    On macOS, scientific-stack libraries (scikit-learn, BLAS, …) create
    GCD/libdispatch worker threads the first time they run an OpenMP parallel
    region, which happens at import time. ``fork()`` without ``exec()`` cannot
    recover GCD state, so a kernel forked from such a warm interpreter deadlocks
    before replying to ``kernel_info``. There we fall back to exec-launched
    kernels (losing the warm-import speedup but staying correct).

    Set :data:`FORK_ENV_VAR` to ``1``/``0`` to override the platform default.
    """
    if (forced := os.environ.get(FORK_ENV_VAR)) is not None:
        return forced.strip().lower() not in {"", "0", "false", "no"}
    return sys.platform != "darwin"


class ForkCmd(TypedDict):
    cmd: Literal["fork"]
    argv: Sequence[str]
    log: str


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


def _locked[**P, R](
    method: Callable[Concatenate[KernelForkServer, P], Awaitable[R]],
) -> Callable[Concatenate[KernelForkServer, P], Awaitable[R]]:
    @wraps(method)
    async def wrapper(self: KernelForkServer, *args: P.args, **kwargs: P.kwargs) -> R:
        async with self._lock:
            return await method(self, *args, **kwargs)

    return wrapper


@dataclass
class KernelForkServer:
    """A server that executes code and allows forking off kernels after."""

    py_cmd: tuple[str, ...]
    code: str
    process: Process | None = field(init=False, default=None)
    # Prevent race conditions with multiple kernels
    _lock: Lock = field(init=False, default_factory=Lock)

    @_locked
    async def fork(self, cmd: Sequence[str], log_path: str) -> int:
        if self.process is None:
            code = RUN_SERVER_CODE.replace('"USER_CODE_INSERTION_POINT"', self.code)
            self.process = await create_subprocess_exec(
                *self.py_cmd, "-c", code, stdin=PIPE, stdout=PIPE, stderr=PIPE
            )

        resp = await self._send_cmd(ForkCmd(cmd="fork", argv=cmd, log=log_path))
        return resp["pid"]

    @_locked
    async def get_exit_code(self, pid: int) -> int | None:
        if self.process is None:
            return None
        resp = await self._send_cmd(ExitCodeCmd(cmd="exit_code", pid=pid))
        return resp["code"]

    @_locked
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
        out = (
            (await self.process.stdout.readline())
            if self.process.returncode is None
            else b""
        )
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            assert self.process.stderr
            err = await self.process.stderr.read()
            msg = (
                "Failed to parse response from fork server:\n"
                f"Stdout: {out.decode('utf-8', errors='replace')}\n"
                f"Stderr: {err.decode('utf-8', errors='replace')}"
            )
            raise RuntimeError(msg) from e


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
    log_path: str | None = field(init=False, default=None)
    _output_surfaced: bool = field(init=False, default=False)
    _shutdown_initiated: bool = field(init=False, default=False)

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
            self._surface_output(code)
        return code

    @override
    async def wait(self) -> int | None:
        if self.pid is None or not self.server:
            return 0
        code = await self.server.wait(self.pid)
        self.pid = None
        self._surface_output(code)
        return code

    def _surface_output(self, code: int) -> None:
        """Log the kernel’s captured output and drop its log file.

        A kernel that crashes on startup (e.g. a broken preload) writes its
        traceback to the log file instead of replying to ``kernel_info``,
        which otherwise surfaces only as a generic “Kernel died” error.
        Emit it on abnormal exit so the cause is visible; on a clean exit just clean up.
        """
        if self._output_surfaced:
            return
        self._output_surfaced = True
        if (log_path := self.log_path) is None:
            return
        self.log_path = None
        try:
            output = Path(log_path).read_text(errors="replace").strip()
        except OSError:
            output = ""
        finally:
            Path(log_path).unlink(missing_ok=True)
        if code != 0 and output and not self._shutdown_initiated:
            self.parent.log.warning(
                "Kernel %s exited with code %d. Captured output:\n%s",
                *(self.kernel_id, code, output),
            )

    @override
    async def send_signal(self, signum: int) -> None:
        assert self.pid
        os.kill(self.pid, signum)

    @override
    async def kill(self, restart: bool = False) -> None:
        self._shutdown_initiated = True
        if self.pid:
            with suppress(ProcessLookupError):
                os.kill(self.pid, signal.SIGKILL)

    @override
    async def terminate(self, restart: bool = False) -> None:
        await self.kill(restart=restart)

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
        fd, self.log_path = tempfile.mkstemp(prefix="sej-kernel-", suffix=".log")
        os.close(fd)
        self.pid = await self.server.fork(kernel_argv, self.log_path)
        self.parent.log.debug(
            "Kernel %s output captured at %s", self.kernel_id, self.log_path
        )
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
        if forking_supported():
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
        self._resources = ExitStack()
        self._reactivate_mpl_inline = self._resources.enter_context(
            importlib.resources.as_file(FILES / "reactivate-mpl-inline.py")
        )

    def __del__(self) -> None:
        self._resources.close()
        super().__del__()

    @override
    def format_kernel_cmd(self, extra_arguments: list[str] | None = None) -> list[str]:
        cmd = super().format_kernel_cmd(extra_arguments=extra_arguments)
        # When not forking (see `forking_supported`),
        # the kernel is exec-launched fresh and never runs `code`,
        # so inject it as startup lines instead.
        if self.code and not forking_supported():
            cmd = [*cmd, f"--IPKernelApp.exec_lines={self.code}"]
        return [*cmd, f"--IPKernelApp.exec_files={self._reactivate_mpl_inline}"]

    @override
    async def finish_shutdown(
        self,
        waittime: float | None = None,
        pollinterval: float = 0.1,
        restart: bool = False,
    ) -> None:
        # For speed, we just kill the kernel
        if self.has_kernel:
            await self.provisioner.kill(restart=restart)
            await self.provisioner.wait()

    _async_finish_shutdown = finish_shutdown


def forking_km_class(code: str) -> type[ForkingKernelManager]:
    class F(ForkingKernelManager):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(code, *args, **kwargs)

    return F
