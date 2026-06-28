# SPDX-License-Identifier: MPL-2.0
"""Mime renderer ignoring HoloViews metadata."""

from __future__ import annotations

from base64 import b64decode
from itertools import chain
from types import MappingProxyType
from typing import TYPE_CHECKING, override

from ipython.core import display
from myst_nb.core.render import MimeRenderPlugin

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from docutils import nodes
    from myst_nb.core.render import MimeData, NbElementRenderer


HV_MIME_TYPES = frozenset(
    {"application/vnd.holoviews_load.v0+json", "application/vnd.holoviews_exec.v0+json"}
)
RASTER_IMAGE_DIMS: Mapping[str, Callable[[bytes], tuple[int, int]] | None] = (
    MappingProxyType(
        {
            "image/png": getattr(display, "_pngxy", None),
            "image/jpeg": getattr(display, "_jpegxy", None),
            "image/gif": getattr(display, "_gifxy", None),
            "image_webp": getattr(display, "_webpxy", None),
        }
    )
)


class SEJMimeRenderer(MimeRenderPlugin):
    """Accepts but ignores HoloViews metadata and adds dimensions to images."""

    mime_priority_overrides = tuple(
        ("*", mt, 1) for mt in chain(HV_MIME_TYPES, RASTER_IMAGE_DIMS)
    )

    @staticmethod
    @override
    def handle_mime(
        renderer: NbElementRenderer, data: MimeData, inline: int
    ) -> None | list[nodes.Element]:
        if not inline and data.mime_type in HV_MIME_TYPES:
            return []
        if not inline and (get_dims := RASTER_IMAGE_DIMS.get(data.mime_type)):
            [elem] = renderer.render_image(data)
            if not (elem.attributes.keys() & {"width", "height"}):
                assert isinstance(data.content, str)
                data_bytes = b64decode(data.content)
                width, height = get_dims(data_bytes)
                elem["width"] = str(width)
                elem["height"] = str(height)
            return [elem]
        return None
