# SPDX-License-Identifier: MPL-2.0
"""Redo matplotlib_inline’s registration for the kernel’s real shell."""

from __future__ import annotations


def _reactivate_mpl_inline() -> None:
    import sys

    if "matplotlib" not in sys.modules:
        return
    import matplotlib as mpl

    backend = mpl.get_backend()
    if not backend.startswith("module://"):
        return
    if (ip := get_ipython()) is None:  # noqa: F821
        return

    from matplotlib_inline.backend_inline import configure_inline_support

    # a one-shot cache on the function itself that survives the fork, so it
    # would otherwise skip re-registering the PNG formatter for this shell
    if hasattr(configure_inline_support, "current_backend"):
        del configure_inline_support.current_backend
    ip.enable_matplotlib(backend)


_reactivate_mpl_inline()
del _reactivate_mpl_inline
