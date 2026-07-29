from __future__ import annotations

import os
import subprocess
from importlib.resources import files
from pathlib import Path

from sidecar_edits import edits as edits


def tool_path(name: str) -> Path:
    path = Path(str(files("sidecar_edits").joinpath("bin", executable_name(name))))
    if not path.exists():
        build_native_tool(name, path)
    if path.exists():
        return path
    raise RuntimeError(f"packaged tool is not built: {name}")


def build_native_tool(name: str, target: Path) -> None:
    if name != "extract_subckts":
        raise RuntimeError(f"unsupported packaged tool: {name}")

    source = Path(str(files("sidecar_edits").joinpath("native", "extract_subckts.c")))
    if not source.exists():
        raise RuntimeError(
            f"packaged tool is not built: {name}. "
            "Install a built wheel or run the package build first."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    compiler = os.environ.get("CC", "cc")
    command = [
        compiler,
        "-Wall",
        "-Wextra",
        "-Werror",
        "-std=c11",
        "-o",
        str(target),
        str(source),
    ]
    try:
        subprocess.run(command, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"failed to build packaged tool {name}: {exc}") from exc


def executable_name(name: str) -> str:
    if os.name == "nt":
        return f"{name}.exe"
    return name
