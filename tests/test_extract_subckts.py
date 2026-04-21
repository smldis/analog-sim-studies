from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "prototype" / "sidecar_edits" / "extract_subckts.c"


def build_extractor(tmp_path: Path) -> Path:
    binary = tmp_path / "extract_subckts"
    subprocess.run(
        ["cc", "-Wall", "-Wextra", "-Werror", "-std=c11", "-o", str(binary), str(SOURCE)],
        check=True,
        capture_output=True,
        text=True,
    )
    return binary


def run_extract(binary: Path, input_file: Path, main_out: Path, subckt_out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), str(input_file), str(main_out), str(subckt_out), subckt_out.name],
        check=False,
        capture_output=True,
        text=True,
    )


def test_extract_moves_one_subckt_block_into_include_and_keeps_top_level_lines(tmp_path: Path) -> None:
    binary = build_extractor(tmp_path)
    input_file = tmp_path / "input.spi"
    main_out = tmp_path / "main.spi"
    subckt_out = tmp_path / "subckts.inc"
    input_file.write_text(
        "V1 in 0 1\n"
        "Rbias in out 10k\n"
        "  .subckt inv a y\n"
        "M1 y a 0 0 nch\n"
        "  .ends inv\n"
        "Xload out 0 1k\n",
        encoding="utf-8",
    )

    result = run_extract(binary, input_file, main_out, subckt_out)

    assert result.returncode == 0, result.stderr
    assert main_out.read_text(encoding="utf-8") == (
        "V1 in 0 1\n"
        "Rbias in out 10k\n"
        '.INCLUDE "subckts.inc"\n'
        "Xload out 0 1k\n"
    )
    assert subckt_out.read_text(encoding="utf-8") == (
        "  .subckt inv a y\n"
        "M1 y a 0 0 nch\n"
        "  .ends inv\n"
    )


def test_extract_moves_multiple_subckt_blocks_with_one_include(tmp_path: Path) -> None:
    binary = build_extractor(tmp_path)
    input_file = tmp_path / "input.spi"
    main_out = tmp_path / "main.spi"
    subckt_out = tmp_path / "subckts.inc"
    input_file.write_text(
        "V1 in 0 1\n"
        ".SUBCKT a x y\n"
        "R1 x y 1k\n"
        ".ENDS a\n"
        "X1 in out a\n"
        "  .subckt b p n\n"
        "C1 p n 1p\n"
        "  .ends b\n"
        "V2 out 0 2\n",
        encoding="utf-8",
    )

    result = run_extract(binary, input_file, main_out, subckt_out)

    assert result.returncode == 0, result.stderr
    assert main_out.read_text(encoding="utf-8") == (
        "V1 in 0 1\n"
        '.INCLUDE "subckts.inc"\n'
        "X1 in out a\n"
        "V2 out 0 2\n"
    )
    assert subckt_out.read_text(encoding="utf-8") == (
        ".SUBCKT a x y\n"
        "R1 x y 1k\n"
        ".ENDS a\n"
        "  .subckt b p n\n"
        "C1 p n 1p\n"
        "  .ends b\n"
    )
