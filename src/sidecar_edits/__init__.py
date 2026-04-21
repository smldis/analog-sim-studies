from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def tool_path(name: str) -> Path:
    path = Path(str(files("sidecar_edits").joinpath("bin", name)))
    if not path.exists():
        raise RuntimeError(
            f"packaged tool is not built: {name}. "
            "Run the package build first, for example `python setup.py build_py`."
        )
    return path
