# SPDX-License-Identifier: MPL-2.0

user_ns = globals().copy()


def __main():
    import json
    import os
    import sys
    import tempfile

    import ipykernel.kernelapp

    for argv in map(json.loads, sys.stdin):
        if child_pid := os.fork():
            print(child_pid)
            sys.stdout.flush()
            continue
        with (
            open("/dev/null") as r,
            tempfile.NamedTemporaryFile("w", prefix=f"kernel-{os.getpid()}-") as w,
        ):
            os.dup2(r.fileno(), sys.stdin.fileno())
            os.dup2(w.fileno(), sys.stdout.fileno())
            os.dup2(w.fileno(), sys.stderr.fileno())

            ipykernel.kernelapp.launch_new_instance(argv, user_ns=user_ns)


__main()
