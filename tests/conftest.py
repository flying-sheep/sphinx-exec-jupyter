# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import pytest

from sphinx_exec_jupyter._kernel_mgr import FORK_ENV_VAR


@pytest.fixture(autouse=True)
def _force_fork(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the forking provisioner regardless of platform default.

    Forking is disabled by default on macOS (see ``forking_supported``),
    but the single-threaded preloads used in the tests are safe to fork,
    so force it on to test the fork code path everywhere.
    Tests for the fallback opt back out.
    """
    monkeypatch.setenv(FORK_ENV_VAR, "1")
