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
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective
from sphinx_design.shared import create_component

from sphinx_exec_jupyter._kernel_mgr import maybe_patch_myst_nb
from sphinx_exec_jupyter._pending import PendingExecNode

from ..common import execute_cells

if TYPE_CHECKING:
    from collections.abc import Iterable

    from myst_nb.sphinx_ import SphinxEnvType

__all__ = ["HoloViewsDirective"]

FILES = files(__name__)
COLLECT_URLS = (FILES / "collect-urls.py").read_text()

# from https://github.com/holoviz-dev/nbsite/blob/e75708a28d9a4ab805753c0520b8eb8779c79d82/nbsite/pyodide/__init__.py#L82
JS_URLS = [
    f"https://cdn.bokeh.org/bokeh/release/bokeh-{BOKEH_VERSION}.min.js",
    f"https://cdn.bokeh.org/bokeh/release/bokeh-widgets-{BOKEH_VERSION}.min.js",
    f"https://cdn.bokeh.org/bokeh/release/bokeh-tables-{BOKEH_VERSION}.min.js",
    f"{CDN_DIST}panel.min.js",
]


def hv_preload(backends: Iterable[str], exec_code: str) -> str:
    return (
        "import holoviews as hv\n"
        f"for backend in {json.dumps(sorted(backends))}:\n"
        f"    hv.extension(backend)\n"
        f"{exec_code}"
    )


def process_hv_results(
    results_raw: list[nodes.Node],
    backends: list[str],
    env: SphinxEnvType,
    docname: str,
) -> list[nodes.Node]:
    n_blocks = 3
    if len(results_raw) != n_blocks * len(backends):
        msg = "Unexpected number of outputs from HoloViews execution:\n" + "\n\n".join(
            n.pformat() for n in results_raw
        )
        raise ExtensionError(msg)

    urls: dict[str, list[str]] = {"js": list(JS_URLS), "css": []}
    results: list[nodes.Node] = []
    for _header, plot, urls_cell in batched(results_raw, n_blocks):
        try:
            new_urls = json.loads(urls_cell.children[1].children[0].astext())
        except Exception as e:
            e.add_note(
                "Unexpected output when collecting HoloViews URLs:\n"
                + urls_cell.pformat()
            )
            raise
        urls["js"] += new_urls["js"]
        urls["css"] += new_urls["css"]
        results.append(plot)

    for url in urls["js"]:
        NbMetadataCollector.add_js_file(env, docname, f"holoviews-{url}", url, {})

    if len(results) == 1:
        return results

    if "sphinx_design" not in env.app.extensions:
        msg = "`sphinx_design` extension is required for multiple backends"
        raise ExtensionError(msg)

    tab_set = create_component("tab-set", classes=["sd-tab-set"])
    for i, (tab_name, plot) in enumerate(zip(backends, results, strict=True)):
        tab_label = nodes.rubric(
            tab_name, "", nodes.Text(tab_name), classes=["sd-tab-label"]
        )
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


def choice_list(argument: str, choices: Iterable[str]) -> list[str]:
    return [
        directives.choice(item.strip(), list(choices)) for item in argument.split(",")
    ]


class HoloViewsDirectiveOptions(TypedDict, total=False):
    backends: list[str]


class HoloViewsDirective(SphinxDirective):
    option_spec = dict(  # noqa: RUF012
        backends=lambda arg: choice_list(arg, hv.extension._backends),  # noqa: SLF001
    )
    has_content = True

    options: HoloViewsDirectiveOptions  # pyright: ignore[reportIncompatibleVariableOverride]

    def run(self) -> list[nodes.Node]:
        backends = self.options.get("backends", self.env.config.holoviews_backends)
        code = "\n".join(self.content)
        cells = [
            block
            for backend in backends
            for block in [f"hv.extension({backend!r})", code, COLLECT_URLS]
        ]

        if self.config.exec_jupyter_isolate_per_document:
            return [PendingExecNode(cells=cells, hv_backends=list(backends))]

        with maybe_patch_myst_nb(
            self.config, code=hv_preload(backends, self.config.exec_jupyter_code)
        ):
            results_raw = execute_cells(cells, self.state.document)
        return process_hv_results(
            results_raw, backends, cast("SphinxEnvType", self.env), self.env.docname
        )
