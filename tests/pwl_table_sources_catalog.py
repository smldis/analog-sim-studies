"""Review catalog for the PWL table source prototype.

This file is intentionally not named ``test_*.py``. It is a review artifact for
choosing the behavior we want before converting selected cases into executable
pytest tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogCase:
    """A candidate behavior for the first PWL table implementation."""

    name: str
    intent: str
    example: str
    expected: str
    decision: str = "review"
    notes: str = ""


CASES = [
    CatalogCase(
        name="parse_csv_with_missing_cells",
        intent=(
            "Convert a CSV table into one waveform per source column while "
            "omitting blank cells instead of treating them as zero."
        ),
        example=(
            "#time,vin,vclk,ireset\n"
            "0,0,0,\n"
            "1n,0.2,1.2,\n"
            "2n,,0,1m\n"
            "5n,1.2,,0\n"
        ),
        expected=(
            "vin -> PWL(0 0 1n 0.2 5n 1.2)\n"
            "vclk -> PWL(0 0 1n 1.2 2n 0)\n"
            "ireset -> PWL(2n 1m 5n 0)"
        ),
        notes="Core happy path from the design document.",
    ),
    CatalogCase(
        name="parse_tab_delimited_spreadsheet_paste",
        intent=(
            "Accept text copied from a spreadsheet range without requiring the "
            "user to save an intermediate file."
        ),
        example=(
            "#time\tvin\tvclk\n"
            "0\t0\t0\n"
            "1n\t0.2\t1.2\n"
            "2n\t\t0\n"
        ),
        expected=(
            "vin -> PWL(0 0 1n 0.2)\n"
            "vclk -> PWL(0 0 1n 1.2 2n 0)"
        ),
        notes=(
            "Implementation choice: auto-detect tab-delimited text, with an "
            "explicit delimiter override available if detection is ambiguous."
        ),
    ),
    CatalogCase(
        name="preserve_spice_text_without_unit_parsing",
        intent=(
            "Keep time and value cells as SPICE text so simulator parameters "
            "and expressions pass through unchanged."
        ),
        example=(
            "#time,vin\n"
            "{t0},{vdd}/2\n"
            "t_stop,VDD\n"
        ),
        expected="vin -> PWL({t0} {vdd}/2 t_stop VDD)",
        notes=(
            "Selected choice: no numeric conversion and no monotonic-time "
            "validation in the first version."
        ),
    ),
    CatalogCase(
        name="allow_single_point_waveform",
        intent=(
            "Allow source columns with fewer than two emitted points instead "
            "of rejecting partially generated or intentionally short data."
        ),
        example=(
            "#time,marker\n"
            "0,\n"
            "1n,1.2\n"
        ),
        expected="marker -> PWL(1n 1.2)",
        notes="Selected choice from review feedback.",
    ),
    CatalogCase(
        name="preserve_column_order",
        intent=(
            "Return waveforms in the same order as source columns so generated "
            "include files stay stable and easy to review."
        ),
        example=(
            "#time,vb,va,vc\n"
            "0,0,1,2\n"
        ),
        expected="iteration order: vb, va, vc",
    ),
    CatalogCase(
        name="render_pwl_wraps_by_default",
        intent=(
            "Wrap long PWL expressions by default using the SPICE continuation "
            "token so generated files stay readable."
        ),
        example=(
            "PwlWaveform with enough points to exceed the default target line "
            "length."
        ),
        expected=(
            "First line starts with PWL(... and following physical lines start "
            "with '+ '."
        ),
        notes=(
            "Selected choice: default target line length around 88 characters. "
            "Exact wrapping can be implementation-defined but deterministic."
        ),
    ),
    CatalogCase(
        name="render_pwl_can_disable_wrapping",
        intent="Allow users or simulators to request a single-line expression.",
        example="waveform.render_pwl(wrap=False)",
        expected="PWL(...) returned on one physical line.",
    ),
    CatalogCase(
        name="file_loader_dispatches_common_formats",
        intent=(
            "Load CSV, TSV, spreadsheet workbooks, and pandas-supported table "
            "formats through one domain-specific file API."
        ),
        example=(
            "waveforms_from_file('startup.csv')\n"
            "waveforms_from_file('startup.tsv')\n"
            "waveforms_from_file('startup.xlsx', sheet='slow_start')\n"
            "waveforms_from_file('startup.ods', sheet='slow_start')"
        ),
        expected=(
            "All calls return the same PwlWaveform mapping for equivalent "
            "table content."
        ),
        notes=(
            "Implementation choice: pandas is acceptable as a dependency. "
            "Specific workbook engines should fail with clear install guidance "
            "if unavailable. If a workbook has exactly one sheet, use it by "
            "default without requiring sheet=..."
        ),
    ),
    CatalogCase(
        name="missing_time_header_reports_clear_error",
        intent="Reject malformed tables that do not have #time as the first column.",
        example=(
            "time,vin\n"
            "0,0\n"
        ),
        expected="Error mentions #time and the first column/header location.",
    ),
    CatalogCase(
        name="duplicate_source_columns_report_clear_error",
        intent="Reject duplicate source names before silently overwriting data.",
        example=(
            "#time,vin,vin\n"
            "0,0,1\n"
        ),
        expected="Error mentions duplicate source column 'vin'.",
    ),
    CatalogCase(
        name="row_with_value_and_empty_time_reports_location",
        intent=(
            "Reject a row that contains emitted source values but has no time "
            "cell, because the generated PWL point would be invalid."
        ),
        example=(
            "#time,vin,vclk\n"
            "0,0,0\n"
            ",1.2,\n"
        ),
        expected="Error mentions the row with the empty #time cell.",
    ),
    CatalogCase(
        name="requested_sheet_missing_reports_available_sheets",
        intent=(
            "Make workbook sheet mistakes fixable without forcing users to "
            "inspect the workbook manually."
        ),
        example="waveforms_from_file('startup.xlsx', sheet='missing')",
        expected="Error mentions requested sheet and available sheet names.",
    ),
    CatalogCase(
        name="workbook_with_one_sheet_uses_it_by_default",
        intent=(
            "Avoid forcing users to specify a sheet name when the workbook has "
            "no ambiguity."
        ),
        example="waveforms_from_file('startup.xlsx') with one worksheet",
        expected="The only worksheet is parsed as the PWL table.",
    ),
    CatalogCase(
        name="workbook_with_multiple_sheets_requires_sheet",
        intent=(
            "Avoid guessing which worksheet contains the PWL table when a "
            "workbook has multiple sheets."
        ),
        example="waveforms_from_file('startup.xlsx') with several worksheets",
        expected="Error asks for sheet=... and mentions available sheet names.",
    ),
    CatalogCase(
        name="surrounding_whitespace_reports_error",
        intent=(
            "Reject ambiguous whitespace around headers, times, or values "
            "instead of silently rewriting user-authored SPICE text."
        ),
        example=(
            "#time, vin\n"
            "0,0\n"
        ),
        expected="Error mentions whitespace and the affected header/cell.",
    ),
    CatalogCase(
        name="empty_source_columns_are_discarded",
        intent=(
            "Ignore source columns that contain no emitted points so users can "
            "keep placeholder columns in spreadsheet workflows."
        ),
        example=(
            "#time,vin,unused\n"
            "0,0,\n"
            "1n,1.2,\n"
        ),
        expected="Only vin is returned.",
    ),
]


# Reviewed alternatives:
#
# - Add explicit helpers such as waveforms_from_csv(), waveforms_from_tsv(), and
#   waveforms_from_excel(). The current catalog assumes one waveforms_from_file()
#   entry point plus waveforms_from_text().
#   Decision: no. Keep one waveforms_from_file() entry point plus
#   waveforms_from_text().
# - Strip whitespace around headers and cells. This can make pasted data more
#   forgiving, but may surprise users if a SPICE expression intentionally
#   contains leading/trailing whitespace. The recommended first choice is to
#   strip headers and empty-cell checks, while preserving non-empty time/value
#   text after minimal surrounding whitespace cleanup.
#   Decision: no. Report whitespace as an error.
# - Keep empty source columns. The current catalog does not decide whether a
#   column with no points should return PwlWaveform(name, points=()) or be
#   rejected. Returning it is more transparent; rejecting it catches typos.
#   Decision: discard empty source columns.
