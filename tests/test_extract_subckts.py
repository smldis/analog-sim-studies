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


def test_extract_accepts_final_line_without_newline(tmp_path: Path) -> None:
    binary = build_extractor(tmp_path)
    input_file = tmp_path / "input.spi"
    main_out = tmp_path / "main.spi"
    subckt_out = tmp_path / "subckts.inc"
    input_file.write_text(
        "V1 in 0 1\n"
        ".SUBCKT inv a y\n"
        "R1 a y 1k\n"
        ".ENDS\n"
        "Rload out 0 1k",
        encoding="utf-8",
    )

    result = run_extract(binary, input_file, main_out, subckt_out)

    assert result.returncode == 0, result.stderr
    assert main_out.read_text(encoding="utf-8") == (
        "V1 in 0 1\n"
        '.INCLUDE "subckts.inc"\n'
        "Rload out 0 1k"
    )
    assert subckt_out.read_text(encoding="utf-8") == (
        ".SUBCKT inv a y\n"
        "R1 a y 1k\n"
        ".ENDS\n"
    )


def test_extract_does_not_delete_existing_dot_tmp_files_on_failure(tmp_path: Path) -> None:
    binary = build_extractor(tmp_path)
    input_file = tmp_path / "input.spi"
    main_out = tmp_path / "main.spi"
    subckt_out = tmp_path / "subckts.inc"
    unrelated_tmp = tmp_path / "main.spi.tmp"
    unrelated_tmp.write_text("keep me\n", encoding="utf-8")
    input_file.write_text(
        ".SUBCKT a x y\n"
        ".SUBCKT nested x y\n"
        ".ENDS\n",
        encoding="utf-8",
    )

    result = run_extract(binary, input_file, main_out, subckt_out)

    assert result.returncode != 0
    assert "nested .SUBCKT detected" in result.stderr
    assert unrelated_tmp.read_text(encoding="utf-8") == "keep me\n"


def test_extract_flushes_excess_pending_lines_to_main(tmp_path: Path) -> None:
    binary = build_extractor(tmp_path)
    input_file = tmp_path / "input.spi"
    main_out = tmp_path / "main.spi"
    subckt_out = tmp_path / "subckts.inc"
    input_file.write_text(
        "\n\n\n\n"
        "V1 in 0 1\n"
        ".SUBCKT a x y\n"
        "R1 x y 1k\n"
        ".ENDS\n",
        encoding="utf-8",
    )

    result = run_extract(binary, input_file, main_out, subckt_out)

    assert result.returncode == 0, result.stderr
    assert main_out.read_text(encoding="utf-8") == (
        "\n\n\n\n"
        "V1 in 0 1\n"
        '.INCLUDE "subckts.inc"\n'
    )
    assert subckt_out.read_text(encoding="utf-8") == (
        ".SUBCKT a x y\n"
        "R1 x y 1k\n"
        ".ENDS\n"
    )
