# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from typing import TYPE_CHECKING, overload

from docutils import nodes

if TYPE_CHECKING:
    from typing import Literal


class PendingExecNode(nodes.General, nodes.Element):
    """Placeholder emitted by directives for deferred per-document execution.

    Attributes
    ----------
    cells
        code strings to execute as notebook cells
    hv_backends
        HoloViews backend names, or None for plain exec-jupyter

    """

    @overload
    def __getitem__(self, key: Literal["cells"]) -> list[str]: ...

    @overload
    def __getitem__(self, key: Literal["hv_backends"]) -> list[str] | None: ...

    def __getitem__(self, key: str) -> object:
        return super().__getitem__(key)
