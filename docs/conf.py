from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
manifest = tomllib.loads((ROOT / "unit.toml").read_text(encoding="utf-8"))
for child in manifest["unit"]["children"]:
    source = ROOT / child / "src"
    if source.is_dir():
        sys.path.insert(0, str(source))

project = "Analog Sim Studies"
author = "smldis"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]
html_theme = "furo"
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
exclude_patterns = ["_build"]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
myst_heading_anchors = 3
