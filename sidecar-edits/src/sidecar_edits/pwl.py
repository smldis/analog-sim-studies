from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_LINE_LENGTH = 88
EXCEL_SUFFIXES = {".xls", ".xlsx", ".xlsm", ".xlsb", ".ods", ".odf", ".odt"}


class PwlTableError(ValueError):
    """Raised when a PWL table cannot be converted into waveforms."""


@dataclass(frozen=True)
class PwlPoint:
    """One emitted time/value pair in a SPICE PWL expression."""

    time: str
    value: str


@dataclass(frozen=True)
class PwlWaveform:
    """Named waveform loaded from one non-empty source column."""

    name: str
    points: tuple[PwlPoint, ...]

    def render_pwl(self, *, wrap: bool = True, line_length: int = DEFAULT_LINE_LENGTH) -> str:
        tokens = [token for point in self.points for token in (point.time, point.value)]
        if not wrap:
            return f"PWL({' '.join(tokens)})"
        return _wrap_pwl_tokens(tokens, line_length=line_length)


def waveforms_from_text(text: str) -> dict[str, PwlWaveform]:
    """Load PWL waveforms from copied or exported delimited text."""

    rows = _read_delimited_text(text)
    return _waveforms_from_rows(rows)


def waveforms_from_file(path: str | Path, *, sheet: str | None = None) -> dict[str, PwlWaveform]:
    """Load PWL waveforms from a delimited file or spreadsheet workbook."""

    table_path = Path(path)
    suffix = table_path.suffix.lower()
    if suffix in EXCEL_SUFFIXES:
        return _waveforms_from_workbook(table_path, sheet=sheet)
    return waveforms_from_text(table_path.read_text(encoding="utf-8"))


def _read_delimited_text(text: str) -> list[list[str]]:
    sample = text.lstrip("\ufeff")
    delimiter = _detect_delimiter(sample)
    return list(csv.reader(StringIO(sample), delimiter=delimiter))


def _waveforms_from_workbook(path: Path, *, sheet: str | None) -> dict[str, PwlWaveform]:
    try:
        workbook = pd.ExcelFile(path)
    except ImportError as exc:
        raise PwlTableError(
            f"cannot read workbook {path}: missing pandas spreadsheet engine ({exc})"
        ) from exc
    sheet_names = list(workbook.sheet_names)
    selected_sheet = _select_sheet(sheet, sheet_names)
    try:
        frame = pd.read_excel(
            path,
            sheet_name=selected_sheet,
            dtype=str,
            keep_default_na=False,
        )
    except ImportError as exc:
        raise PwlTableError(
            f"cannot read workbook {path}: missing pandas spreadsheet engine ({exc})"
        ) from exc
    rows = [list(frame.columns)]
    rows.extend([list(row) for row in frame.itertuples(index=False, name=None)])
    return _waveforms_from_rows(rows)


def _select_sheet(requested: str | None, sheet_names: list[str]) -> str:
    if requested is not None:
        if requested in sheet_names:
            return requested
        raise PwlTableError(
            f"requested sheet={requested!r} was not found; available sheets: "
            f"{', '.join(sheet_names)}"
        )
    if len(sheet_names) == 1:
        return sheet_names[0]
    raise PwlTableError(
        "workbook has multiple sheets; pass sheet=...; available sheets: "
        f"{', '.join(sheet_names)}"
    )


def _waveforms_from_rows(rows: list[list[object]]) -> dict[str, PwlWaveform]:
    if not rows:
        raise PwlTableError("PWL table is empty; first column must be #time")

    header = [_cell_text(cell) for cell in rows[0]]
    _validate_no_surrounding_whitespace(header, location="header")
    if not header or header[0] != "#time":
        raise PwlTableError("PWL table #time header must be in the first column")
    _validate_source_names(header[1:])

    points_by_name = {name: [] for name in header[1:]}
    for row_number, row in enumerate(rows[1:], start=2):
        cells = [_cell_text(cell) for cell in row]
        cells.extend([""] * (len(header) - len(cells)))
        cells = cells[: len(header)]
        _validate_no_surrounding_whitespace(cells, location=f"row {row_number}")

        time = cells[0]
        values = cells[1:]
        if time == "" and any(value != "" for value in values):
            raise PwlTableError(f"row {row_number} has source values but empty #time cell")
        if time == "":
            continue
        for name, value in zip(header[1:], values, strict=True):
            if value != "":
                points_by_name[name].append(PwlPoint(time=time, value=value))

    return {
        name: PwlWaveform(name=name, points=tuple(points))
        for name, points in points_by_name.items()
        if points
    }


def _cell_text(cell: object) -> str:
    if pd.isna(cell):
        return ""
    return str(cell)


def _detect_delimiter(text: str) -> str:
    first_line = text.partition("\n")[0]
    counts = {delimiter: first_line.count(delimiter) for delimiter in (",", "\t", ";")}
    delimiter, count = max(counts.items(), key=lambda item: item[1])
    if count > 0:
        return delimiter
    try:
        return csv.Sniffer().sniff(text, delimiters=",\t;").delimiter
    except csv.Error:
        return ","


def _validate_source_names(names: list[str]) -> None:
    seen = set()
    for name in names:
        if name == "":
            raise PwlTableError("source column names must not be empty")
        if name in seen:
            raise PwlTableError(f"duplicate source column {name!r}")
        seen.add(name)


def _validate_no_surrounding_whitespace(cells: Iterable[str], *, location: str) -> None:
    for cell in cells:
        if cell != "" and cell != cell.strip():
            raise PwlTableError(
                f"{location} cell has surrounding whitespace around {cell.strip()!r}; "
                "remove it instead of relying on implicit cleanup"
            )


def _wrap_pwl_tokens(tokens: list[str], *, line_length: int) -> str:
    if not tokens:
        return "PWL()"

    lines: list[str] = []
    current = "PWL("
    for index, token in enumerate(tokens):
        suffix = ")" if index == len(tokens) - 1 else ""
        separator = "" if current.endswith("(") else " "
        candidate = f"{current}{separator}{token}{suffix}"
        if len(candidate) <= line_length:
            current = candidate
            continue
        if current != "PWL(":
            lines.append(current)
            current = f"+ {token}{suffix}"
        else:
            current = f"PWL({token}{suffix}"
    if current:
        if not current.endswith(")"):
            current = f"{current})"
        lines.append(current)
    return "\n".join(lines)
