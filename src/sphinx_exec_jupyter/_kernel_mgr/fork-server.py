# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import builtins

builtins.__IPYTHON__ = True

del builtins

"USER_CODE_INSERTION_POINT"

user_ns = globals().copy()


def __main() -> None:  # noqa: C901
    import json
    import os
    import signal
    import sys
    import tempfile
    from pathlib import Path
    from typing import TYPE_CHECKING

    import ipykernel.kernelapp

    if TYPE_CHECKING:
        from typing import Never

        from sphinx_exec_jupyter._kernel_mgr import Cmd

    exit_codes: dict[int, int] = {}

    def reap_children(signum: int, frame: object) -> None:  # noqa: ARG001
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:  # no reapable children right now
                    break
                exit_codes[pid] = os.waitstatus_to_exitcode(status)
            except ChildProcessError:
                break

    signal.signal(signal.SIGCHLD, reap_children)

    def launch(argv: list[str]) -> Never:
        with (
            Path(os.devnull).open() as r,
            tempfile.NamedTemporaryFile("w", prefix=f"kernel-{os.getpid()}-") as w,
        ):
            os.dup2(r.fileno(), sys.stdin.fileno())
            os.dup2(w.fileno(), sys.stdout.fileno())
            os.dup2(w.fileno(), sys.stderr.fileno())
            ipykernel.kernelapp.launch_new_instance(argv, user_ns=user_ns)
            sys.exit(0)  # actually unreachable

    for line in sys.stdin:
        msg: Cmd = json.loads(line)
        if msg["cmd"] == "fork":
            if child_pid := os.fork():
                json.dump({"pid": child_pid}, sys.stdout)
                sys.stdout.write("\n")
                sys.stdout.flush()
                continue
            launch(list(msg["argv"]))

        if msg["cmd"] == "exit_code":
            code = exit_codes.get(msg["pid"])
        elif msg["cmd"] == "wait":
            while (code := exit_codes.get(msg["pid"])) is None:
                signal.pause()  # wait until `SIGCHLD` triggers the handler above
        json.dump({"code": code}, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()


if __name__ == "__main__":
    __main()
