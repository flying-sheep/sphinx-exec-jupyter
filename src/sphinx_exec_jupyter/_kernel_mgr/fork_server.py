# SPDX-License-Identifier: MPL-2.0


def __main():
    globals().pop("__main", None)

    import json
    import os
    import signal
    import sys
    from threading import Event

    import ipykernel.kernelapp

    child_event = Event()
    stop_event = Event()

    assert sys.argv[1] == "-c"
    argv = json.loads(sys.argv[2])

    signal.signal(signal.SIGUSR1, lambda sig, frame: child_event.set())
    signal.signal(signal.SIGINT, lambda sig, frame: stop_event.set())
    signal.signal(signal.SIGTERM, lambda sig, frame: stop_event.set())

    while not stop_event.is_set():
        if child_event.is_set():
            child_event.clear()
            if child_pid := os.fork():
                print(child_pid)
            else:
                ipykernel.kernelapp.launch_new_instance(argv)
        # better signal.sleep that handles SIGINT and SIGTERM
        stop_event.wait(timeout=1.0)


__main()
