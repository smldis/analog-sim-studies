"""Analytical regressions for the AC helper in each runnable study.
Extract only the pure function: importing a study also builds execution objects.
"""
import ast
import cmath
import math
from pathlib import Path
from typing import Mapping

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["ota_pvt.py", "ota_pvt_clean.py", "ota_pvt_clean_nested.py"])
def measure(request):
    path = ROOT / "studies" / request.param
    tree = ast.parse(path.read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "measure_ac_metrics"
    )
    namespace = {"Mapping": Mapping, "math": math, "cmath": cmath, "RawFileError": ValueError}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    return namespace["measure_ac_metrics"]


def columns(frequencies, transfer):
    return {
        "frequency": [complex(frequency) for frequency in frequencies],
        "v(out)": [transfer(frequency) for frequency in frequencies],
        "v(in_p)": [1 + 0j] * len(frequencies),
        "v(in_n)": [0j] * len(frequencies),
    }


def test_three_pole_crossing_keeps_continuous_phase(measure):
    # H(f)=8/(1+jf)^3 has |H|=1 and phase=-180 at f=sqrt(3).
    # The bracket straddles the principal phase discontinuity.
    actual = measure(columns([1, 1.6, 1.8, 3, 10], lambda frequency: 8 / (1 + 1j * frequency) ** 3))
    assert actual["gain_bandwidth_hz"] == pytest.approx(math.sqrt(3), rel=0.002)
    assert actual["phase_margin_deg"] == pytest.approx(0, abs=0.2)


def test_single_pole_analytic_unity_and_phase(measure):
    frequencies = [10 ** (index / 40) for index in range(241)]
    actual = measure(columns(frequencies, lambda frequency: 100 / (1 + 1j * frequency / 100)))
    assert actual["gain_bandwidth_hz"] == pytest.approx(100 * math.sqrt(9999), rel=0.0001)
    expected = 180 - math.degrees(math.atan(math.sqrt(9999)))
    assert actual["phase_margin_deg"] == pytest.approx(expected, abs=0.002)


def test_reported_gain_tracks_first_ac_sample_not_dc(measure):
    frequencies = [10 ** (index / 20) for index in range(121)]
    transfer = lambda frequency: 100 / (1 + 1j * frequency / 100)
    low = measure(columns(frequencies, transfer))
    high = measure(columns([frequency for frequency in frequencies if frequency >= 1000], transfer))
    assert low["dc_gain_db"] == pytest.approx(20 * math.log10(abs(transfer(1))))
    assert high["dc_gain_db"] == pytest.approx(20 * math.log10(abs(transfer(1000))))
    assert high["gain_bandwidth_hz"] == low["gain_bandwidth_hz"]
    assert low["dc_gain_db"] - high["dc_gain_db"] > 20
