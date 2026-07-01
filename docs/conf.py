# SPDX-License-Identifier: MPL-2.0
"""Configuration for Sphinx documentation."""

from __future__ import annotations

import os
from importlib.metadata import metadata
from pathlib import PurePosixPath
from urllib.parse import urlparse, urlunparse

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

_gh_url = urlparse(os.environ.get("READTHEDOCS_GIT_CLONE_URL", "").removesuffix(".git"))

html_theme_options = dict(
    source_repository=urlunparse(_gh_url),
    source_branch=os.environ.get("READTHEDOCS_GIT_IDENTIFIER"),
    source_directory="docs",
)
html_context = dict(
    github_user=PurePosixPath(_gh_url.path).parts[0],
    github_repo=PurePosixPath(_gh_url.path).parts[1],
    github_version=os.environ.get("READTHEDOCS_GIT_IDENTIFIER"),
    current_version=os.environ.get("READTHEDOCS_VERSION"),
    slug=os.environ.get("READTHEDDOCS_PROJECT"),
)
