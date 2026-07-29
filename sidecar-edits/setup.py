from __future__ import annotations

import os
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from wheel.bdist_wheel import bdist_wheel


class BuildPyWithNativeTools(build_py):
    def run(self) -> None:
        super().run()
        self.build_extract_subckts()

    def build_extract_subckts(self) -> None:
        root = Path(__file__).resolve().parent
        source = root / "src" / "sidecar_edits" / "native" / "extract_subckts.c"
        executable = "extract_subckts.exe" if os.name == "nt" else "extract_subckts"
        target = Path(self.build_lib) / "sidecar_edits" / "bin" / executable
        target.parent.mkdir(parents=True, exist_ok=True)

        compiler = os.environ.get("CC", "cc")
        subprocess.run(
            [
                compiler,
                "-Wall",
                "-Wextra",
                "-Werror",
                "-std=c11",
                "-o",
                str(target),
                str(source),
            ],
            check=True,
        )


class BinaryWheel(bdist_wheel):
    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False


setup(cmdclass={"build_py": BuildPyWithNativeTools, "bdist_wheel": BinaryWheel})
