from __future__ import annotations

import importlib.metadata
import os
import sys
from datetime import datetime
from pathlib import Path

# -- Path setup --------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

project = "sobe"
author = "Liz Balbuena"
copyright = f"{datetime.now():%Y}, {author}"
try:
    version = importlib.metadata.version(project)
except importlib.metadata.PackageNotFoundError:
    version = "0.0.0"
release = version

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_class_signature = "separated"
napoleon_google_docstring = True
napoleon_numpy_docstring = False
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "boto3": ("https://boto3.amazonaws.com/v1/documentation/api/latest/", None),
}

templates_path = ["_templates"]
exclude_patterns: list[str] = []

# -- Options for HTML output -------------------------------------------------
html_theme = "furo"
html_static_path = ["_static"]
html_title = f"{project} {release}"
html_logo = None
html_theme_options = {
    "sidebar_hide_name": False,
}

# -- Extensions configuration ------------------------------------------------
# Fail on warnings in CI (Read the Docs sets READTHEDOCS env variable)
if os.getenv("READTHEDOCS"):
    nitpicky = True

# -- Custom substitutions ----------------------------------------------------

rst_prolog = """
.. |project| replace:: sobe
.. |pkg| replace:: sobe
"""
