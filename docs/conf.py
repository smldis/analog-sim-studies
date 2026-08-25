from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sources(unit_root: Path) -> None:
    """Put every unit's package on the path, however deeply it is composed.

    Composition is recursive, so a unit's children are units in their own
    right: `hedloom` contains `flow`, `exec` and `run`. Walking only the root
    manifest reached the front door and stopped, which is why an API page could
    document `hedloom` but not the `Site` it hands you.
    """

    source = unit_root / "src"
    if source.is_dir():
        sys.path.insert(0, str(source))
    manifest_path = unit_root / "unit.toml"
    if not manifest_path.is_file():
        return
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    for child in manifest["unit"].get("children", []):
        _sources(unit_root / child)


_sources(ROOT)

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
