# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import json
from importlib.metadata import version
from importlib.resources import files
from itertools import batched
from typing import TYPE_CHECKING, TypedDict

import holoviews as hv
import myst_nb.docutils_
import myst_nb.sphinx_ext
from docutils import nodes
from docutils.parsers.rst import directives
from myst_nb.sphinx_ import NbMetadataCollector
from nbformat import v4
from panel.io.convert import BOKEH_VERSION
from panel.io.resources import CDN_DIST
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata
from sphinx_design.shared import create_component

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.application import Sphinx

__all__ = ["setup", "HoloviewsDirective"]

FILES = files(__name__)
COLLECT_URLS = (FILES / "collect-urls.py").read_text()

# from https://github.com/holoviz-dev/nbsite/blob/e75708a28d9a4ab805753c0520b8eb8779c79d82/nbsite/pyodide/__init__.py#L82
JS_URLS = {
    "bokeh": [
        f"https://cdn.bokeh.org/bokeh/release/bokeh-{BOKEH_VERSION}.min.js",
        f"https://cdn.bokeh.org/bokeh/release/bokeh-widgets-{BOKEH_VERSION}.min.js",
        f"https://cdn.bokeh.org/bokeh/release/bokeh-tables-{BOKEH_VERSION}.min.js",
        f"{CDN_DIST}panel.min.js",
    ],
    "plotly": [],
    "matplotlib": [],
}


def execute_cells(cells: list[str], document: nodes.document) -> list[nodes.Node]:
    """Execute code cells and return resulting docutils nodes, one per cell."""
    notebook_json = json.dumps(
        v4.new_notebook(cells=[v4.new_code_cell(cell) for cell in cells])
    )
    document.settings.nb_execution_mode = "force"

    parser = myst_nb.docutils_.Parser()
    after_last_child = len(document.children)
    parser.parse(notebook_json, document)
    nodes = document.children[after_last_child:]
    del document.children[after_last_child:]
    return nodes


def choice_list(argument: str, choices: Iterable[str]) -> list[str]:
    return [
        directives.choice(item.strip(), list(choices)) for item in argument.split(",")
    ]


class HoloviewsOptions(TypedDict, total=False):
    backends: list[str]


class HoloviewsDirective(SphinxDirective):
    option_spec = dict(
        backends=lambda arg: choice_list(arg, hv.extension._backends),
    )
    has_content = True

    options: HoloviewsOptions  # pyright: ignore[reportIncompatibleVariableOverride]

    def run(self) -> list[nodes.Node]:
        backends = self.options.get("backends", ["bokeh"])

        code = "\n".join(self.content)
        results_raw = execute_cells(
            [
                block
                for backend in backends
                for block in [
                    f"import holoviews as hv\nhv.extension({backend!r})",
                    code,
                    COLLECT_URLS,
                ]
            ],
            self.state.document,
        )

        urls = {"js": [url for b in backends for url in JS_URLS[b]], "css": []}
        results: list[nodes.Node] = []
        for _header, plot, urls_cell in batched(results_raw, 3, strict=True):
            # container → output (second child) → literal (first child) → text
            new_urls = json.loads(urls_cell.children[1].children[0].astext())
            urls["js"] += new_urls["js"]
            urls["css"] += new_urls["css"]
            results.append(plot)

        for url in urls["js"]:
            key = f"holoviews-{url}"
            NbMetadataCollector.add_js_file(self.env, self.env.docname, key, url, {})

        if len(results) == 1:
            return list(results[0])

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


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_directive("holoviews", HoloviewsDirective)

    app.connect("config-inited", myst_nb.sphinx_ext.add_exclude_patterns)
    app.connect("build-finished", myst_nb.sphinx_ext.add_global_html_resources)
    app.connect("html-page-context", myst_nb.sphinx_ext.add_per_page_html_resources)

    return ExtensionMetadata(
        version=version("sphinx-exec-jupyter"),
        parallel_read_safe=True,
        parallel_write_safe=True,
    )
