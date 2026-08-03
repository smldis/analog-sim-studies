from __future__ import annotations

import ast
import builtins
from dataclasses import replace
import inspect
import io
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "docs" / "reference" / "ota-pvt-plan"
ASS_FLOW_SRC = ROOT / "ass-flow" / "src"
SIDECAR_EDITS_SRC = ROOT / "sidecar-edits" / "src"
for source_root in (ASS_FLOW_SRC, SIDECAR_EDITS_SRC, REFERENCE_DIR):
    sys.path.insert(0, str(source_root))

import ota_pvt_plan as reference  # noqa: E402
from ass_flow import (  # noqa: E402
    BindingError,
    CollectionInputBinding,
    OutputReference,
    PlanValidationError,
    input_artifact,
    plain_data,
    plan,
    submit,
)
from sidecar_edits import edits as sidecar_edit_api  # noqa: E402
from sidecar_edits.render import load_editfile  # noqa: E402


EXPECTED_POINTS = (
    ("tt_1v80_27c", "tt", 1.80, 27),
    ("ss_1v62_125c", "ss", 1.62, 125),
    ("ff_1v98_m40c", "ff", 1.98, -40),
)

EXPECTED_SOURCE_URIS = (
    "docs/reference/ota-pvt-plan/inputs/base",
    "docs/reference/ota-pvt-plan/inputs/pvt_edits.py",
    "docs/reference/ota-pvt-plan/inputs/measurement_definition.json",
    "docs/reference/ota-pvt-plan/inputs/spec_limits.json",
)

EXPECTED_OPERATION_CONTRACTS = {
    "reference.ota_pvt.prepare_run": {
        "version": "1",
        "inputs": {
            "base": ("sidecar-base-directory", "scalar", True),
            "edits": ("sidecar-edit-file", "scalar", True),
        },
        "config": {
            "param_set": (str, True),
            "point_id": (str, True),
            "process": (str, True),
            "temp_c": (int, True),
            "vdd_v": (float, True),
        },
        "outputs": {"run": "prepared-simulation-directory"},
        "resources": (("cpu_cores", 1, "count"),),
    },
    "reference.ota_pvt.canonicalize_deck": {
        "version": "1",
        "inputs": {
            "run": ("prepared-simulation-directory", "scalar", True),
        },
        "config": {
            "deck_relpath": (str, True),
            "spice_format": (str, True),
            "top_name": (str, True),
        },
        "outputs": {"canonical": "canonical-netlist"},
        "resources": (),
    },
    "reference.ota_pvt.decompose_ota": {
        "version": "1",
        "inputs": {
            "canonical": ("canonical-netlist", "scalar", True),
        },
        "config": {
            "circuit_name": (str, True),
            "max_level": (int, True),
            "suppress_false_stacks": (bool, True),
            "vdd_nets": (list, True),
            "vss_nets": (list, True),
        },
        "outputs": {"decomposition": "ota-functional-decomposition"},
        "resources": (("cpu_cores", 1, "count"),),
    },
    "reference.ota_pvt.simulate_ac": {
        "version": "1",
        "inputs": {
            "run": ("prepared-simulation-directory", "scalar", True),
        },
        "config": {
            "analysis": (str, True),
            "point_id": (str, True),
            "process": (str, True),
            "simulator_profile": (str, True),
            "temp_c": (int, True),
            "vdd_v": (float, True),
        },
        "outputs": {"raw": "simulator-raw-results"},
        "resources": (
            ("cpu_cores", 1, "count"),
            ("memory_gib", 1, "GiB"),
        ),
    },
    "reference.ota_pvt.measure_ac": {
        "version": "1",
        "inputs": {
            "definition": ("ota-measurement-definition", "scalar", True),
            "raw": ("simulator-raw-results", "scalar", True),
        },
        "config": {"point_id": (str, True)},
        "outputs": {"measurements": "ota-point-measurements"},
        "resources": (),
    },
    "reference.ota_pvt.evaluate_pvt": {
        "version": "1",
        "inputs": {
            "decompositions": (
                "ota-functional-decomposition",
                "collection",
                True,
            ),
            "limits": ("ota-specification-limits", "scalar", True),
            "measurements": ("ota-point-measurements", "collection", True),
        },
        "config": {"point_ids": (list, True)},
        "outputs": {"evaluation": "ota-pvt-evaluation"},
        "resources": (),
    },
}

POINT_OUTPUT_PRODUCERS = {
    "prepared": ("prepare-run", "run"),
    "canonical": ("canonicalize-deck", "canonical"),
    "decomposition": ("decompose-ota", "decomposition"),
    "raw": ("simulate-ac", "raw"),
    "measurements": ("measure-ac", "measurements"),
}


def _config(invocation):
    return {binding.name: plain_data(binding.value) for binding in invocation.config}


def _point_boundaries(normalized):
    return {
        boundary.authored_key.removeprefix("point-"): boundary
        for boundary in normalized.boundaries
        if boundary.authored_key and boundary.authored_key.startswith("point-")
    }


def _point_invocations(normalized, point_id):
    boundary = _point_boundaries(normalized)[point_id]
    return {
        invocation.authored_key: invocation
        for invocation in normalized.invocations
        if invocation.boundary_id == boundary.id
    }


def _evaluation(normalized):
    return next(
        invocation
        for invocation in normalized.invocations
        if invocation.authored_key == "evaluate-pvt"
    )


def _operation_contract(definition):
    return {
        "version": definition.identity.version,
        "inputs": {
            contract.name: (
                contract.artifact.kind,
                contract.cardinality,
                contract.required,
            )
            for contract in definition.inputs
        },
        "config": {
            contract.name: (contract.value_type, contract.required)
            for contract in definition.config
        },
        "outputs": {
            contract.name: contract.artifact.kind
            for contract in definition.outputs
        },
        "resources": tuple(
            (resource.name, resource.amount, resource.unit)
            for resource in definition.resources
        ),
    }


def test_reference_has_the_exact_versioned_normalized_shape_and_named_outputs():
    normalized = reference.build_plan()

    assert normalized.validate() is normalized
    assert (
        len(normalized.sources),
        len(normalized.operations),
        len(normalized.flows),
        len(normalized.boundaries),
        len(normalized.invocations),
        len(normalized.edges),
        len(normalized.outputs),
    ) == (4, 6, 2, 4, 16, 18, 16)

    assert [(point.key, point.process, point.vdd_v, point.temp_c) for point in reference.PVT_POINTS] == list(
        EXPECTED_POINTS
    )
    assert {
        definition.identity.name: _operation_contract(definition)
        for definition in normalized.operations
    } == EXPECTED_OPERATION_CONTRACTS
    assert {
        (definition.identity.name, definition.identity.version)
        for definition in normalized.flows
    } == {
        ("reference.ota_pvt.point", "1"),
        ("reference.ota_pvt.study", "1"),
    }

    expected_outputs = {
        "evaluation": OutputReference(_evaluation(normalized).id, "evaluation")
    }
    for point_id, *_ in EXPECTED_POINTS:
        point_invocations = _point_invocations(normalized, point_id)
        for output_suffix, (producer_key, producer_output) in (
            POINT_OUTPUT_PRODUCERS.items()
        ):
            expected_outputs[f"points__{point_id}__{output_suffix}"] = (
                OutputReference(
                    point_invocations[producer_key].id,
                    producer_output,
                )
            )
    assert {
        output.name: output.reference for output in normalized.outputs
    } == expected_outputs


def test_every_boundary_and_invocation_is_keyed_with_stable_plan_identity():
    first = reference.build_plan()
    second = reference.build_plan()

    assert all(invocation.authored_key for invocation in first.invocations)
    assert all(boundary.authored_key for boundary in first.boundaries)
    assert {boundary.authored_key for boundary in first.boundaries} == {
        "ota-pvt-study",
        *(f"point-{point_id}" for point_id, *_ in EXPECTED_POINTS),
    }
    study = next(
        boundary
        for boundary in first.boundaries
        if boundary.authored_key == "ota-pvt-study"
    )
    assert study.parent_id is None
    assert {
        boundary.parent_id
        for boundary in first.boundaries
        if boundary.authored_key != "ota-pvt-study"
    } == {study.id}

    assert first.to_data() == second.to_data()
    assert first.to_json() == second.to_json()
    assert json.loads(first.to_json()) == first.to_data()
    for field in ("sources", "invocations", "edges", "boundaries"):
        assert [item.id for item in getattr(first, field)] == [
            item.id for item in getattr(second, field)
        ]
    assert all(edge.id.startswith("edge:key:") for edge in first.edges)


def test_each_point_forks_after_preparation_and_resolves_exact_pvt_config():
    normalized = reference.build_plan()
    invocations_by_id = {invocation.id: invocation for invocation in normalized.invocations}

    for point_id, process, vdd_v, temp_c in EXPECTED_POINTS:
        point_invocations = _point_invocations(normalized, point_id)
        assert set(point_invocations) == {
            "prepare-run",
            "canonicalize-deck",
            "decompose-ota",
            "simulate-ac",
            "measure-ac",
        }
        prepared = point_invocations["prepare-run"]
        canonical = point_invocations["canonicalize-deck"]
        decomposition = point_invocations["decompose-ota"]
        simulated = point_invocations["simulate-ac"]
        measured = point_invocations["measure-ac"]

        assert _config(prepared) == {
            "param_set": point_id,
            "point_id": point_id,
            "process": process,
            "temp_c": temp_c,
            "vdd_v": vdd_v,
        }
        assert _config(simulated) == {
            "analysis": "ac",
            "point_id": point_id,
            "process": process,
            "simulator_profile": "ngspice-ac",
            "temp_c": temp_c,
            "vdd_v": vdd_v,
        }
        assert _config(canonical) == {
            "deck_relpath": "ota_ac.cir",
            "spice_format": "ngspice",
            "top_name": "ota_pvt",
        }
        assert _config(decomposition) == {
            "circuit_name": "ota_core",
            "max_level": 4,
            "suppress_false_stacks": True,
            "vdd_nets": ["vdd"],
            "vss_nets": ["vss"],
        }
        assert _config(measured) == {"point_id": point_id}

        point_edges = [
            edge
            for edge in normalized.edges
            if edge.target_invocation_id in {
                canonical.id,
                decomposition.id,
                simulated.id,
                measured.id,
            }
            and edge.target_member_index is None
        ]
        assert {
            (
                edge.source.invocation_id,
                edge.target_invocation_id,
                edge.target_input_name,
            )
            for edge in point_edges
        } == {
            (prepared.id, canonical.id, "run"),
            (prepared.id, simulated.id, "run"),
            (canonical.id, decomposition.id, "canonical"),
            (simulated.id, measured.id, "raw"),
        }
        assert all(
            invocations_by_id[edge.source.invocation_id].boundary_id
            == prepared.boundary_id
            for edge in point_edges
        )


def test_evaluation_preserves_both_collection_orders_and_member_positions():
    normalized = reference.build_plan()
    evaluation = _evaluation(normalized)
    bindings = {binding.name: binding for binding in evaluation.inputs}
    expected_point_ids = [point_id for point_id, *_ in EXPECTED_POINTS]
    point_id_by_boundary = {
        boundary.id: boundary.authored_key.removeprefix("point-")
        for boundary in normalized.boundaries
        if boundary.authored_key and boundary.authored_key.startswith("point-")
    }
    invocations_by_id = {invocation.id: invocation for invocation in normalized.invocations}

    assert _config(evaluation) == {"point_ids": expected_point_ids}
    for input_name, producer_key in (
        ("measurements", "measure-ac"),
        ("decompositions", "decompose-ota"),
    ):
        binding = bindings[input_name]
        assert isinstance(binding, CollectionInputBinding)
        assert [
            point_id_by_boundary[
                invocations_by_id[reference_value.invocation_id].boundary_id
            ]
            for reference_value in binding.references
        ] == expected_point_ids
        assert all(
            invocations_by_id[reference_value.invocation_id].authored_key == producer_key
            for reference_value in binding.references
        )

        positioned_edges = sorted(
            (
                edge
                for edge in normalized.edges
                if edge.target_invocation_id == evaluation.id
                and edge.target_input_name == input_name
            ),
            key=lambda edge: edge.target_member_index,
        )
        assert [edge.target_member_index for edge in positioned_edges] == [0, 1, 2]
        assert [edge.source for edge in positioned_edges] == list(binding.references)


def test_policies_and_resources_remain_descriptive_plain_plan_data():
    normalized = reference.build_plan()
    simulation_definition = next(
        definition
        for definition in normalized.operations
        if definition.identity.name == "reference.ota_pvt.simulate_ac"
    )
    simulation_invocations = [
        invocation
        for invocation in normalized.invocations
        if invocation.operation == simulation_definition.identity
    ]

    assert simulation_definition.default_policy == reference.SIMULATOR_BOUNDARY_POLICY
    assert all(
        invocation.policy == reference.SIMULATOR_BOUNDARY_POLICY
        for invocation in simulation_invocations
    )
    assert all(
        invocation.policy in {
            reference.PLAN_DECLARATION_POLICY,
            reference.SIMULATOR_BOUNDARY_POLICY,
        }
        for invocation in normalized.invocations
    )
    assert {
        definition.identity.name: tuple(
            (resource.name, resource.amount, resource.unit)
            for resource in definition.resources
        )
        for definition in normalized.operations
    } == {
        name: contract["resources"]
        for name, contract in EXPECTED_OPERATION_CONTRACTS.items()
    }
    serialized = normalized.to_data()
    assert all(isinstance(invocation["policy"], dict) for invocation in serialized["invocations"])
    assert all(isinstance(operation["resources"], list) for operation in serialized["operations"])


def test_planning_avoids_common_file_open_paths_and_imports_no_sibling_or_runtime_code(
    monkeypatch,
):
    source = (REFERENCE_DIR / "ota_pvt_plan.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots == {"__future__", "ass_flow", "dataclasses"}
    assert "sidecar_edits" not in source
    assert "spice_canonical" not in source
    assert "netlist_decomposition" not in source

    def refuse_file_io(*args, **kwargs):
        raise AssertionError("build_plan attempted file I/O")

    monkeypatch.setattr(builtins, "open", refuse_file_io)
    monkeypatch.setattr(io, "open", refuse_file_io)
    monkeypatch.setattr(os, "open", refuse_file_io)
    monkeypatch.setattr(Path, "open", refuse_file_io)
    monkeypatch.setattr(Path, "read_bytes", refuse_file_io)
    monkeypatch.setattr(Path, "read_text", refuse_file_io)
    normalized = reference.build_plan()
    assert len(normalized.invocations) == 16


def test_refusing_bodies_are_not_needed_for_planning_and_submit_still_refuses():
    normalized = reference.build_plan()
    assert normalized.validate() is normalized

    for declaration in reference.OPERATION_DECLARATIONS:
        positional = []
        keywords = {}
        for parameter_value in inspect.signature(declaration._function).parameters.values():
            if parameter_value.kind is inspect.Parameter.KEYWORD_ONLY:
                keywords[parameter_value.name] = None
            else:
                positional.append(None)
        with pytest.raises(NotImplementedError, match="plan declaration only"):
            declaration._function(*positional, **keywords)

    with pytest.raises(NotImplementedError, match="outside this planning spike"):
        submit(normalized)


def test_authoring_and_plan_validation_reject_kind_config_order_and_position_defects():
    with plan() as draft:
        base = input_artifact("base", "sidecar-base-directory")
        edits = input_artifact("edits.py", "sidecar-edit-file")
        with pytest.raises(BindingError, match="expects float"):
            reference.prepare_run.options(key="wrong-config")(
                base,
                edits,
                point_id="tt_1v80_27c",
                param_set="tt_1v80_27c",
                process="tt",
                vdd_v=1,
                temp_c=27,
            )
        with pytest.raises(BindingError, match="expects artifact kind"):
            reference.canonicalize_deck.options(key="wrong-kind")(
                base,
                deck_relpath="ota_ac.cir",
                spice_format="ngspice",
                top_name="ota_pvt",
            )
    empty = draft.finish(outputs={})
    assert empty.invocations == ()

    normalized = reference.build_plan()
    evaluation = _evaluation(normalized)
    measurements = next(
        binding for binding in evaluation.inputs if binding.name == "measurements"
    )
    reversed_measurements = CollectionInputBinding(
        "measurements", tuple(reversed(measurements.references))
    )
    malformed_evaluation = replace(
        evaluation,
        inputs=tuple(
            reversed_measurements if binding.name == "measurements" else binding
            for binding in evaluation.inputs
        ),
    )
    malformed_order = replace(
        normalized,
        invocations=tuple(
            malformed_evaluation if invocation.id == evaluation.id else invocation
            for invocation in normalized.invocations
        ),
    )
    with pytest.raises(PlanValidationError) as order_caught:
        malformed_order.validate()
    assert "edge_binding_mismatch" in {
        issue.code for issue in order_caught.value.issues
    }

    first_measurement_edge = next(
        edge
        for edge in normalized.edges
        if edge.target_invocation_id == evaluation.id
        and edge.target_input_name == "measurements"
        and edge.target_member_index == 0
    )
    malformed_position = replace(
        normalized,
        edges=tuple(
            replace(edge, target_member_index=1)
            if edge.id == first_measurement_edge.id
            else edge
            for edge in normalized.edges
        ),
    )
    with pytest.raises(PlanValidationError) as position_caught:
        malformed_position.validate()
    assert {
        "duplicate_target_edge",
        "missing_dependency_edge",
    }.issubset({issue.code for issue in position_caught.value.issues})


def test_fixture_paths_are_repository_relative_and_sidecar_values_match_points():
    normalized = reference.build_plan()
    assert tuple(source.uri for source in normalized.sources) == EXPECTED_SOURCE_URIS
    assert all(not Path(uri).is_absolute() and ".." not in Path(uri).parts for uri in EXPECTED_SOURCE_URIS)
    assert all((ROOT / uri).exists() for uri in EXPECTED_SOURCE_URIS)

    edit_path = REFERENCE_DIR / "inputs" / "pvt_edits.py"
    render_plan = load_editfile(edit_path)
    assert render_plan.base_dir == (REFERENCE_DIR / "inputs" / "base").resolve()
    assert render_plan.edits
    assert all(sidecar_edit_api.is_edit_spec(edit) for edit in render_plan.edits)
    assert [
        (
            param_set.name,
            param_set.params["process"],
            param_set.params["vdd_v"],
            param_set.params["temp_c"],
        )
        for param_set in render_plan.param_sets
    ] == list(EXPECTED_POINTS)
    assert all(
        param_set.params["point_id"] == param_set.name
        and param_set.params["param_set"] == param_set.name
        for param_set in render_plan.param_sets
    )

    measurement_definition = json.loads(
        (REFERENCE_DIR / "inputs" / "measurement_definition.json").read_text(
            encoding="utf-8"
        )
    )
    limits = json.loads(
        (REFERENCE_DIR / "inputs" / "spec_limits.json").read_text(encoding="utf-8")
    )
    assert [metric["name"] for metric in measurement_definition["metrics"]] == [
        "dc_gain_db",
        "gain_bandwidth_hz",
        "phase_margin_deg",
    ]
    assert limits["status"] == "provisional-reference-only"
