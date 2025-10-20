# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

from typing import TYPE_CHECKING

from myst_nb.core.render import MimeRenderPlugin

if TYPE_CHECKING:
    from docutils import nodes
    from myst_nb.core.render import MimeData, NbElementRenderer

HV_MIME_TYPES = frozenset(
    {"application/vnd.holoviews_load.v0+json", "application/vnd.holoviews_exec.v0+json"}
)


class HoloViewsMimeRenderer(MimeRenderPlugin):
    mime_priority_overrides = [("*", mt, 1) for mt in HV_MIME_TYPES]

    @staticmethod
    def handle_mime(
        renderer: NbElementRenderer, data: MimeData, inline: int
    ) -> None | list[nodes.Element]:
        if not inline and data.mime_type in HV_MIME_TYPES:
            return []
        return None
