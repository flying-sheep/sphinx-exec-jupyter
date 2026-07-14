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
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

master_doc = "index"

# extensions

intersphinx_mapping = dict(
    python=("https://docs.python.org/3/", None),
    holoviz=("https://holoviews.org/", None),
)
nb_execution_show_tb = os.environ.get("READTHEDOCS") == "True"

# Theme stuff

html_theme = "furo"

if _gh_url := os.environ.get("READTHEDOCS_GIT_CLONE_URL"):
    _gh_url = _gh_url.removesuffix(".git")
    _gh_user, _gh_repo = PurePosixPath(urlparse(_gh_url).path).parts[1:]
else:
    _gh_user = _gh_repo = None

_git_id = (
    None  # this would have to be the base branch of the PR
    if os.environ.get("READTHEDOCS_VERSION_TYPE") == "external"
    else os.environ.get("READTHEDOCS_GIT_IDENTIFIER")
)

html_theme_options = dict(
    source_repository=(_gh_url or ""),
    source_branch=_git_id,
    source_directory="docs",
)
html_context = dict(
    READTHEDOCS=os.environ.get("READTHEDOCS") == "True",
    display_github=True,
    github_user=_gh_user,
    github_repo=_gh_repo,
    github_version=_git_id,
    current_version=os.environ.get("READTHEDOCS_VERSION"),
    slug=os.environ.get("READTHEDDOCS_PROJECT"),
)
