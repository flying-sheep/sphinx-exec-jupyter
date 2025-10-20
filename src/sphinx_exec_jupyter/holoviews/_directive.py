# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
from importlib.resources import files
from itertools import batched
from typing import TYPE_CHECKING, TypedDict, cast

import holoviews as hv
from docutils import nodes
from docutils.parsers.rst import directives
from myst_nb.sphinx_ import NbMetadataCollector
from panel.io.convert import BOKEH_VERSION
from panel.io.resources import CDN_DIST
from sphinx.util.docutils import SphinxDirective
from sphinx_design.shared import create_component

from ..common import execute_cells
from ._mime_render import HoloViewsMimeRenderer

if TYPE_CHECKING:
    from collections.abc import Iterable

    from myst_nb.sphinx_ import SphinxEnvType

__all__ = ["HoloViewsDirective", "HoloViewsMimeRenderer"]

FILES = files(__name__)
COLLECT_URLS = (FILES / "collect-urls.py").read_text()

# from https://github.com/holoviz-dev/nbsite/blob/e75708a28d9a4ab805753c0520b8eb8779c79d82/nbsite/pyodide/__init__.py#L82
JS_URLS = [
    f"https://cdn.bokeh.org/bokeh/release/bokeh-{BOKEH_VERSION}.min.js",
    f"https://cdn.bokeh.org/bokeh/release/bokeh-widgets-{BOKEH_VERSION}.min.js",
    f"https://cdn.bokeh.org/bokeh/release/bokeh-tables-{BOKEH_VERSION}.min.js",
    f"{CDN_DIST}panel.min.js",
]


def choice_list(argument: str, choices: Iterable[str]) -> list[str]:
    return [
        directives.choice(item.strip(), list(choices)) for item in argument.split(",")
    ]


class HoloViewsDirectiveOptions(TypedDict, total=False):
    backends: list[str]


class HoloViewsDirective(SphinxDirective):
    option_spec = dict(
        backends=lambda arg: choice_list(arg, hv.extension._backends),
    )
    has_content = True

    options: HoloViewsDirectiveOptions  # pyright: ignore[reportIncompatibleVariableOverride]

    def run(self) -> list[nodes.Node]:
        backends = self.options.get("backends", self.env.config.holoviews_backends)

        code = "\n".join(self.content)
        cells = [
            block
            for backend in backends
            for block in [
                f"import holoviews as hv\nhv.extension({backend!r})",
                code,
                COLLECT_URLS,
            ]
        ]
        n_blocks_per_backend = 3
        assert len(cells) == n_blocks_per_backend * len(backends)
        results_raw = execute_cells(
            cells,
            self.state.document,
            env=cast("SphinxEnvType", self.env),
        )
        if (len(results_raw) % n_blocks_per_backend) != 0:
            raise self.error(
                "Unexpected number of outputs from HoloViews execution:\n"
                f"{'\n\n'.join(n.pformat() for n in results_raw)}"
            )

        urls = {"js": JS_URLS, "css": []}
        results: list[nodes.Node] = []
        for _header, plot, urls_cell in batched(results_raw, n_blocks_per_backend):
            try:
                # container → output (second child) → literal (first child) → text
                new_urls = json.loads(urls_cell.children[1].children[0].astext())
            except Exception as e:
                e.add_note(
                    f"Unexpected output when collecting HoloViews URLs:\n{urls_cell.pformat()}"
                )
                raise
            urls["js"] += new_urls["js"]
            urls["css"] += new_urls["css"]
            results.append(plot)

        for url in urls["js"]:
            key = f"holoviews-{url}"
            NbMetadataCollector.add_js_file(
                cast("SphinxEnvType", self.env), self.env.docname, key, url, {}
            )

        if len(results) == 1:
            return list(results)

        if "sphinx_design" not in self.env.app.extensions:
            raise self.error(
                "`sphinx_design` extension is required for multiple backends"
            )

        tab_set = create_component("tab-set", classes=["sd-tab-set"])
        for i, (tab_name, plot) in enumerate(zip(backends, results)):
            textnodes, _ = self.state.inline_text(tab_name, self.lineno)
            tab_label = nodes.rubric(tab_name, "", *textnodes, classes=["sd-tab-label"])
            tab_content = create_component(
                "tab-content", classes=["sd-tab-content"], children=[plot]
            )
            tab_item = create_component(
                "tab-item",
                classes=["sd-tab-item"],
                children=[tab_label, tab_content],
                selected=i == 0,
            )
            tab_set += tab_item
        return [tab_set]
