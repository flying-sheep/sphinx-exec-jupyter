# SPDX-License-Identifier: MPL-2.0
from importlib.metadata import metadata

_meta = metadata("sphinx-holoviews")
project = _meta["name"]
author = _meta["author-email"].split('"')[1]
release = _meta["version"]

extensions = [
    "sphinx_holoviews",
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

master_doc = "index"

html_theme = "furo"
# html_static_path = ["_static"]
