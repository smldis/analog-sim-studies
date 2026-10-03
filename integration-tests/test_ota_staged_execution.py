"""Dynamic corner discovery runs from the caller with one execution slot."""

import json
from pathlib import Path
import shutil

import pytest

from hedloom import Site, runtime
from studies import ota_pvt_clean_nested as staged


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="requires real local ngspice")
def test_dynamic_corners_record_plan_and_reuse_without_worker_nesting(tmp_path):
    root = Path(__file__).resolve().parents[1]
    site = Site(records_dir=str(tmp_path / "records"), work_dir=str(tmp_path / "work"),
                runs_dir=str(tmp_path / "runs"), placements={"local": 1},
                address_spaces={"repository-relative": str(root)})
    with runtime(site) as live:
        discovery, corners, written = staged.run_stages(live, name="first")
        again_discovery, again_corners, again_written = staged.run_stages(live, name="again")

    jobs = discovery.outputs["jobs"].value
    assert len(jobs) == 3
    assert len(corners.report.outcomes) == 10
    assert all(run.succeeded for run in (discovery, corners, written,
                                         again_discovery, again_corners, again_written))
    assert len(again_discovery.report.reused) == 2
    assert len(again_corners.report.reused) == 10
    assert again_corners.outputs["evaluation"].value == corners.outputs["evaluation"].value
    assert len({run.run_id for run in (discovery, corners, written)}) == 3

    saved_plan = json.loads(Path(written.outputs["corner_plan"].value).read_text())
    assert saved_plan == dict(staged.corner_study(jobs).document)
    report = Path(written.outputs["report"].value).read_text()
    for job in jobs:
        assert job["name"] in report
    assert "ota_pvt_nested.simulate_ac" in report
    assert written.outputs["verdict"].value["corners"] == 3
