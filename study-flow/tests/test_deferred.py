from __future__ import annotations

import json

from ass_study_flow.cli import main
from ass_study_flow.deferred import DEFERRED_CAPABILITIES


def test_deferred_catalog_names_unimplemented_seams() -> None:
    capability_ids = {item.capability_id for item in DEFERRED_CAPABILITIES}

    assert "durable-reconciliation" in capability_ids
    assert "evidence-promotion" in capability_ids
    assert "executor-routing" in capability_ids
    assert "adaptive-planning" in capability_ids


def test_cli_can_report_deferred_seams_without_starting_dask(capsys) -> None:
    assert main(["--list-deferred"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert {item["capability_id"] for item in payload} == {
        item.capability_id for item in DEFERRED_CAPABILITIES
    }
