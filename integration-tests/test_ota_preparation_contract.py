"""Actual OTA consumers must publish directories with selected Sidecar values."""
from pathlib import Path

import pytest

from studies import ota_pvt as full
from studies import ota_pvt_clean as clean
from studies import ota_pvt_clean_nested as nested
from hedloom import Site, address, input_artifact, local, study


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("form", ["explicit-params", "declarations", "selector"])
def test_prepared_directory_contains_selected_values_and_keeps_spice_expressions(tmp_path, form):
    point = full.PVT_POINTS[1]  # Non-nominal values expose silently unchanged seeds.

    @study(name="ota-preparation-contract", default_policy=local())
    def subject():
        base = input_artifact(address("repository-relative", full.BASE_DIRECTORY_LOCATOR), artifact=full.SIDE_CAR_BASE)
        edits = input_artifact(address("repository-relative", full.PVT_EDITS_LOCATOR), artifact=full.SIDE_CAR_EDITS)
        if form == "explicit-params":
            prepared = full.prepare_run(base, edits, point_id=point.key, param_set=point.key,
                                        process=point.process, vdd_v=point.vdd_v, temp_c=point.temp_c)
        elif form == "declarations":
            prepared = clean.prepare(base, edits, name=point.key,
                declarations={"PARAM_SETS": clean.PVT_DECLARATIONS["PARAM_SETS"][1:2]})
        else:
            prepared = nested.prepare_corner(base, edits, name=point.key, selector=point.key)
        return {"prepared": prepared.run}

    site = Site(root=str(tmp_path / "records"), workspace_root=str(tmp_path / "work"),
                history_root=str(tmp_path / "history"), address_spaces={"repository-relative": str(ROOT)})
    run = subject().submit(site=site, name="prepare", sequential=True)
    assert run.succeeded, run.summary()
    output = run.outputs["prepared"]
    assert output.available
    directory = Path(output.value)
    assert directory.is_dir()
    deck = (directory / "ota_ac.cir").read_text()
    assert "* PVT point=ss_1v62_125c process=ss vdd_v=1.62 temp_c=125" in deck
    assert ".param vdd_v=1.62\n" in deck
    assert ".temp 125\n" in deck
    assert "VDD vdd 0 {vdd_v}\n" in deck
    assert "VINP in_p 0 dc={vdd_v/2} ac=0.5\n" in deck
    assert "VINN in_n 0 dc={vdd_v/2} ac=-0.5\n" in deck
