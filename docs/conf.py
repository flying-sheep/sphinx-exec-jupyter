# SPDX-License-Identifier: MPL-2.0
"""Configuration for Sphinx documentation."""

from __future__ import annotations

import os
from importlib.metadata import metadata
from pathlib import PurePosixPath
from urllib.parse import urlparse

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

if _gh_url := os.environ.get("READTHEDOCS_GIT_CLONE_URL"):
    _gh_url = _gh_url.removesuffix(".git")
    print("GH path:", PurePosixPath(urlparse(_gh_url).path).parts)
    _gh_user, _gh_repo = PurePosixPath(urlparse(_gh_url).path).parts
else:
    _gh_user = _gh_repo = None
print("GH info:", _gh_user, _gh_repo)

html_theme_options = dict(
    source_repository=(_gh_url or ""),
    source_branch=os.environ.get("READTHEDOCS_GIT_IDENTIFIER"),
    source_directory="docs",
)
html_context = dict(
    github_user=_gh_user,
    github_repo=_gh_repo,
    github_version=os.environ.get("READTHEDOCS_GIT_IDENTIFIER"),
    current_version=os.environ.get("READTHEDOCS_VERSION"),
    slug=os.environ.get("READTHEDDOCS_PROJECT"),
)
