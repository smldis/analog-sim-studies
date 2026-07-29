from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sidecar_edits import pwl  # noqa: E402


def rendered(waveforms: dict[str, pwl.PwlWaveform]) -> dict[str, str]:
    return {name: waveform.render_pwl(wrap=False) for name, waveform in waveforms.items()}


def write_workbook(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)


def test_parse_csv_with_missing_cells() -> None:
    waveforms = pwl.waveforms_from_text(
        "#time,vin,vclk,ireset\n"
        "0,0,0,\n"
        "1n,0.2,1.2,\n"
        "2n,,0,1m\n"
        "5n,1.2,,0\n"
    )

    assert rendered(waveforms) == {
        "vin": "PWL(0 0 1n 0.2 5n 1.2)",
        "vclk": "PWL(0 0 1n 1.2 2n 0)",
        "ireset": "PWL(2n 1m 5n 0)",
    }


def test_parse_tab_delimited_spreadsheet_paste_by_auto_detection() -> None:
    waveforms = pwl.waveforms_from_text(
        "#time\tvin\tvclk\n"
        "0\t0\t0\n"
        "1n\t0.2\t1.2\n"
        "2n\t\t0\n"
    )

    assert rendered(waveforms) == {
        "vin": "PWL(0 0 1n 0.2)",
        "vclk": "PWL(0 0 1n 1.2 2n 0)",
    }


def test_preserve_spice_text_without_unit_parsing() -> None:
    waveforms = pwl.waveforms_from_text(
        "#time,vin\n"
        "{t0},{vdd}/2\n"
        "t_stop,VDD\n"
    )

    assert rendered(waveforms) == {
        "vin": "PWL({t0} {vdd}/2 t_stop VDD)",
    }


def test_allow_single_point_waveform() -> None:
    waveforms = pwl.waveforms_from_text(
        "#time,marker\n"
        "0,\n"
        "1n,1.2\n"
    )

    assert rendered(waveforms) == {
        "marker": "PWL(1n 1.2)",
    }


def test_preserve_column_order() -> None:
    waveforms = pwl.waveforms_from_text(
        "#time,vb,va,vc\n"
        "0,0,1,2\n"
    )

    assert list(waveforms) == ["vb", "va", "vc"]


def test_render_pwl_wraps_by_default() -> None:
    waveform = pwl.PwlWaveform(
        name="vin",
        points=tuple(
            pwl.PwlPoint(time=f"{index}n", value=f"{index / 10:.1f}")
            for index in range(12)
        ),
    )

    text = waveform.render_pwl()

    assert "\n+ " in text
    assert text.startswith("PWL(")
    assert all(len(line) <= 88 for line in text.splitlines())


def test_render_pwl_can_disable_wrapping() -> None:
    waveform = pwl.PwlWaveform(
        name="vin",
        points=tuple(
            pwl.PwlPoint(time=f"{index}n", value=f"{index / 10:.1f}")
            for index in range(12)
        ),
    )

    text = waveform.render_pwl(wrap=False)

    assert "\n" not in text
    assert text.startswith("PWL(")
    assert text.endswith(")")


def test_file_loader_dispatches_csv_and_tsv(tmp_path: Path) -> None:
    csv_path = tmp_path / "startup.csv"
    tsv_path = tmp_path / "startup.tsv"
    csv_path.write_text("#time,vin\n0,0\n1n,1.2\n", encoding="utf-8")
    tsv_path.write_text("#time\tvin\n0\t0\n1n\t1.2\n", encoding="utf-8")

    assert rendered(pwl.waveforms_from_file(csv_path)) == {
        "vin": "PWL(0 0 1n 1.2)",
    }
    assert rendered(pwl.waveforms_from_file(tsv_path)) == {
        "vin": "PWL(0 0 1n 1.2)",
    }


def test_workbook_with_one_sheet_uses_it_by_default(
    tmp_path: Path,
) -> None:
    xlsx_path = tmp_path / "startup.xlsx"
    write_workbook(
        xlsx_path,
        {
            "startup": pd.DataFrame({"#time": ["0", "1n"], "vin": ["0", "1.2"]}),
        },
    )

    assert rendered(pwl.waveforms_from_file(xlsx_path)) == {
        "vin": "PWL(0 0 1n 1.2)",
    }


def test_workbook_with_multiple_sheets_requires_sheet(
    tmp_path: Path,
) -> None:
    xlsx_path = tmp_path / "startup.xlsx"
    write_workbook(
        xlsx_path,
        {
            "fast": pd.DataFrame({"#time": ["0"], "vin": ["0"]}),
            "slow": pd.DataFrame({"#time": ["0"], "vin": ["1"]}),
        },
    )

    with pytest.raises(pwl.PwlTableError, match="sheet=.*fast.*slow"):
        pwl.waveforms_from_file(xlsx_path)


def test_requested_sheet_missing_reports_available_sheets(
    tmp_path: Path,
) -> None:
    xlsx_path = tmp_path / "startup.xlsx"
    write_workbook(
        xlsx_path,
        {
            "fast": pd.DataFrame({"#time": ["0"], "vin": ["0"]}),
            "slow": pd.DataFrame({"#time": ["0"], "vin": ["1"]}),
        },
    )

    with pytest.raises(pwl.PwlTableError, match="missing.*fast.*slow"):
        pwl.waveforms_from_file(xlsx_path, sheet="missing")


def test_missing_time_header_reports_clear_error() -> None:
    with pytest.raises(pwl.PwlTableError, match="#time.*first column"):
        pwl.waveforms_from_text(
            "time,vin\n"
            "0,0\n"
        )


def test_duplicate_source_columns_report_clear_error() -> None:
    with pytest.raises(pwl.PwlTableError, match="duplicate.*vin"):
        pwl.waveforms_from_text(
            "#time,vin,vin\n"
            "0,0,1\n"
        )


def test_row_with_value_and_empty_time_reports_location() -> None:
    with pytest.raises(pwl.PwlTableError, match="row 3.*#time"):
        pwl.waveforms_from_text(
            "#time,vin,vclk\n"
            "0,0,0\n"
            ",1.2,\n"
        )


def test_surrounding_whitespace_reports_error() -> None:
    with pytest.raises(pwl.PwlTableError, match="whitespace.*vin"):
        pwl.waveforms_from_text(
            "#time, vin\n"
            "0,0\n"
        )


def test_empty_source_columns_are_discarded() -> None:
    waveforms = pwl.waveforms_from_text(
        "#time,vin,unused\n"
        "0,0,\n"
        "1n,1.2,\n"
    )

    assert rendered(waveforms) == {
        "vin": "PWL(0 0 1n 1.2)",
    }
