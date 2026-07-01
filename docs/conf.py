# SPDX-License-Identifier: MPL-2.0
"""Configuration for Sphinx documentation."""

from __future__ import annotations

import os
from importlib.metadata import metadata

_meta = metadata("sphinx-exec-jupyter")
project = _meta["name"]
author = _meta["author-email"].split('"')[1]
release = _meta["version"]

extensions = [
    "sphinx_exec_jupyter",
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

master_doc = "index"

html_theme = "furo"

html_theme_options = dict(
    source_repository=os.environ.get("READTHEDOCS_GIT_CLONE_URL", "").removesuffix(
        ".git"
    ),
    source_branch=os.environ.get("READTHEDOCS_GIT_IDENTIFIER", ""),
    source_directory="docs",
)
