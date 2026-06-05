# SPDX-License-Identifier: MPL-2.0


def __main():
    globals().pop("__main", None)

    import json
    import os
    import sys

    import ipykernel.kernelapp

    argv = json.loads(sys.argv[1])

    for _ in sys.stdin:
        if child_pid := os.fork():
            print(child_pid)
            sys.stdout.flush()
            continue
        with open("/dev/null") as r, open("/dev/null", "w") as w:
            os.dup2(r.fileno(), 0)
            os.dup2(w.fileno(), 1)
            os.dup2(w.fileno(), 2)

            ipykernel.kernelapp.launch_new_instance(argv)


__main()
