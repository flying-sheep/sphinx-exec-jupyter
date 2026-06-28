# SPDX-License-Identifier: MPL-2.0
"""Mime renderer ignoring HoloViews metadata."""

from __future__ import annotations

import struct
from base64 import b64decode
from itertools import chain
from typing import TYPE_CHECKING, override

from myst_nb.core.render import MimeRenderPlugin

if TYPE_CHECKING:
    from docutils import nodes
    from myst_nb.core.render import MimeData, NbElementRenderer


HV_MIME_TYPES = frozenset(
    {"application/vnd.holoviews_load.v0+json", "application/vnd.holoviews_exec.v0+json"}
)
PNG_MIME_TYPE = "image/png"


class SEJMimeRenderer(MimeRenderPlugin):
    """Accepts but ignores HoloViews metadata and adds dimensions to PNGs."""

    mime_priority_overrides = tuple(
        ("*", mt, 1) for mt in chain(HV_MIME_TYPES, [PNG_MIME_TYPE])
    )

    @staticmethod
    @override
    def handle_mime(
        renderer: NbElementRenderer, data: MimeData, inline: int
    ) -> None | list[nodes.Element]:
        if not inline and data.mime_type in HV_MIME_TYPES:
            return []
        if not inline and data.mime_type == PNG_MIME_TYPE:
            [elem] = renderer.render_image(data)
            if not (elem.attributes.keys() & {"width", "height"}):
                assert isinstance(data.content, str)
                width, height = _pngxy(b64decode(data.content))
                elem["width"] = str(width)
                elem["height"] = str(height)
            return [elem]
        return None


def _pngxy(data: bytes) -> tuple[int, int]:
    """Read the (width, height) from a PNG header."""
    ihdr = data.index(b"IHDR")
    # next 8 bytes are width/height
    return struct.unpack(">ii", data[ihdr + 4 : ihdr + 12])
