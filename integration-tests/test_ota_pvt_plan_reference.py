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
HEDLOOM_FLOW_SRC = ROOT / "hedloom" / "flow" / "src"
SIDECAR_EDITS_SRC = ROOT / "sidecar-edits" / "src"
for source_root in (HEDLOOM_FLOW_SRC, SIDECAR_EDITS_SRC, REFERENCE_DIR):
    sys.path.insert(0, str(source_root))

import ota_pvt_plan as reference  # noqa: E402
from hedloom_flow import (  # noqa: E402
    ArtifactSourceReference,
    BindingError,
    CollectionInputBinding,
    OutputReference,
    PlanValidationError,
    address,
    artifact,
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

EXPECTED_SOURCES = (
    (
        "docs/reference/ota-pvt-plan/inputs/base",
        "sidecar-base-directory",
        "directory-tree",
        {},
    ),
    (
        "docs/reference/ota-pvt-plan/inputs/pvt_edits.py",
        "sidecar-edit-file",
        "python-source",
        {"encoding": "utf-8"},
    ),
    (
        "docs/reference/ota-pvt-plan/inputs/measurement_definition.json",
        "ota-measurement-definition",
        "json",
        {"encoding": "utf-8"},
    ),
    (
        "docs/reference/ota-pvt-plan/inputs/spec_limits.json",
        "ota-specification-limits",
        "json",
        {"encoding": "utf-8"},
    ),
)

EXPECTED_PLAN_IDS = {
    "sources": (
        "source:0001",
        "source:0002",
        "source:0003",
        "source:0004",
    ),
    "invocations": (
        "invoke:key:ade7d1fc983cd7d1de0f969a48ba67674a70ed65f8ae642f754cb7b000bc3056",
        "invoke:key:57faa364282e74cb71f7b4323fb3e7e1cb6533966461b672d594bf8e3c96dc34",
        "invoke:key:002b1df6a83a0da67c93806d8fdb3f77594b78695a848a3af739ff8ea2bb4794",
        "invoke:key:7a6371d0425f94590fec6ba97c296e69b7a4728911ee0bfca36a2805b11f7bce",
        "invoke:key:0998cd9979c2d926e7b73e5986591469f90514115d275486359998cdb35f6d44",
        "invoke:key:5ec0097a93bc5fc201c8b0c86ee6ab3789ffe517a04823bdc6b34c96c9be2c27",
        "invoke:key:503432b8fc4199eb541e4c91ebafdfcd8b8483d1b29941f168118b62f32dede9",
        "invoke:key:5c4168e357eca0e5ac7d9e30cd3c196135e1bfdc00dd3446ff926dc00b826656",
        "invoke:key:ed47cb970d0f7c431fce73919f56a14c632b5a580763c9174d17010d1c919c5b",
        "invoke:key:331efb1126b6e471f4a8cf862fd48d63ae70abde44a7b11f56710ad4e09cb2e2",
        "invoke:key:3855bc2b8eda94691cff9a0e05f9eefdfaff904008ccf11e5ad1ace2bc3d4548",
        "invoke:key:bcdf25d8b52eb363ec36df3354cc72ac891fa0236121c53b8eda9d25ead24051",
        "invoke:key:752a2699133ebc807ca0f22f77b238c6821c4970b5726e09125a2bc091e672ca",
        "invoke:key:428a14c6331f575fb8fc75033c19cd4ce85033413c03a7e79a6682e5f050b80a",
        "invoke:key:77ff1c490193e021960000397a8d334de9328e7c5d31de9ab620c092c9439d4f",
        "invoke:key:18c7c892dfbbc936b64f43f8ecb98c18fe72384fd80b89ae23afaf2ad007cbe7",
    ),
    "boundaries": (
        "flow:key:847c24bea984e47c92dceeb3ddcf69090b448d82c6cbc079e358eb5c6b670aff",
        "flow:key:0be3465b4f3c395324c49c0e77dba8572778b5e7c8ab87a02092c845bc217454",
        "flow:key:fbf7523c821af1d4d4e17ee4064ab98f8faa2bc56f0d5f09b5946e41b39673bd",
        "flow:key:714e8a36431a7612f2ccbdaf8d9842221503344d6f8995d15d00d09121a7fec5",
    ),
    "edges": (
        "edge:key:cc3d1357bf45133128c4952bf9af757b8006d963fcd89ad0d3e6f7f1eb637442",
        "edge:key:8326a15c4ecfd7bef0bd7b5098ffd2ea99d0c77ff993c802128699707cc8d6a0",
        "edge:key:49145308eb239a539dd25111f01ac9664b13cd2686ff322e569bd1574e5e4e9f",
        "edge:key:894b3ff17ed2d0d3181d1443f46f43ba49c5653bdafcbc8941a76afc375f85a0",
        "edge:key:c3cf24c2df6f653acd9365525c42975fb982dc6a2c9c10dbd34fa20bd8a81df4",
        "edge:key:f5f6c4a09a3421badd9342d19884d9f6d9606cc5ce8c2cee29bd80c3af970448",
        "edge:key:c6883362e8df754ad36a31eec418f99a1ed9a87b57b1a738b0dac6e59fd12cfb",
        "edge:key:cacf3c256b2204123db8e9a6e080b4f6e209514e932ae40d79567ff913d9f5cb",
        "edge:key:1d79a70b8d8d3242ae8a0fbe8cd836ebc2dbde4fca9f2705d5013621960a5da0",
        "edge:key:1af419a5bda540c148df047acff7a8c387fc3eb49dd9a52bcb931f2eca05c111",
        "edge:key:ed00d6a1bb40df8e8a0d702b840260a12e0ec45094d50311bb6dc94e895e8849",
        "edge:key:d5ec85eb762cca234e1b8a71168d42f03ddbc9e6c33c8c6db72918c847ab6446",
        "edge:key:05de609a27fff8168a281f3690ec330220485d1237f50325f3c4e3f993556cf0",
        "edge:key:2db139c4ca11ff9730e9450791a39a348869b0c776d82db8324dd7376960edf9",
        "edge:key:bb29cffeb6fd255740001833e0636f6d808d1ed55101a189135504eedabab162",
        "edge:key:7ecbed98688d2f8908f86e017af54de51faf69def089436b339e46ae53e55672",
        "edge:key:0a4af0642df6fc0a90f916583065513dac2a15924c8b25139c9c6d23104925a3",
        "edge:key:2b32a4d33f548cdc778c0346a09bce0072bf3808bab6478662c80629411121f4",
    ),
}

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
        "outputs": {"run": ("prepared-simulation-directory", None)},
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
        "outputs": {"canonical": ("canonical-netlist", None)},
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
        "outputs": {"decomposition": ("ota-functional-decomposition", None)},
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
        "outputs": {"raw": ("simulator-raw-results", None)},
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
        "outputs": {"measurements": ("ota-point-measurements", None)},
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
        "outputs": {"evaluation": ("ota-pvt-evaluation", None)},
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
            contract.name: (
                contract.artifact.kind,
                contract.can_materialize_as,
            )
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
    # Schema 3: an operation definition may carry what implements it and where
    # each output lands. The reference declares neither, so its shape below is
    # unchanged — only the version it is written in moved.
    assert normalized.schema_version == 3
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
        assert tuple(item.id for item in getattr(first, field)) == (
            EXPECTED_PLAN_IDS[field]
        )
    assert all(edge.id.startswith("edge:key:") for edge in first.edges)


def test_sources_declare_exact_data_only_representations_and_value_classes():
    normalized = reference.build_plan()
    serialized = normalized.to_data()

    assert [
        (
            source.address.address_space,
            source.address.locator,
            source.artifact.kind,
            source.materialized_as.address_space,
            source.materialized_as.access_scope,
            source.materialized_as.codec.name,
            source.materialized_as.codec.version,
            plain_data(source.materialized_as.codec.options),
        )
        for source in normalized.sources
    ] == [
        (
            "repository-relative",
            locator,
            kind,
            "repository-relative",
            "repository-checkout",
            codec_name,
            "1",
            options,
        )
        for locator, kind, codec_name, options in EXPECTED_SOURCES
    ]
    assert serialized["sources"] == [
        {
            "id": f"source:{index:04d}",
            "address": {
                "address_space": "repository-relative",
                "locator": locator,
            },
            "artifact": {"kind": kind},
            "materialized_as": {
                "codec": {
                    "name": codec_name,
                    "version": "1",
                    "options": options,
                },
                "address_space": "repository-relative",
                "access_scope": "repository-checkout",
            },
        }
        for index, (locator, kind, codec_name, options) in enumerate(
            EXPECTED_SOURCES, start=1
        )
    ]

    references = [
        reference_value
        for invocation in normalized.invocations
        for binding in invocation.inputs
        for reference_value in (
            binding.references
            if isinstance(binding, CollectionInputBinding)
            else (binding.reference,)
        )
    ]
    source_references = [
        value for value in references if isinstance(value, ArtifactSourceReference)
    ]
    output_references = [
        value for value in references if isinstance(value, OutputReference)
    ]
    serialized_references = [
        reference_data
        for invocation in serialized["invocations"]
        for binding in invocation["inputs"]
        for reference_data in (
            binding["references"]
            if binding["cardinality"] == "collection"
            else (binding["reference"],)
        )
    ]
    assert len(source_references) == 10
    assert all(value.value_class == "artifact" for value in source_references)
    assert len(output_references) == 18
    assert all(value.value_class == "ephemeral" for value in output_references)
    assert [
        value["value_class"]
        for value in serialized_references
        if value["type"] == "source"
    ] == ["artifact"] * 10
    assert [
        value["value_class"]
        for value in serialized_references
        if value["type"] == "output"
    ] == ["ephemeral"] * 18
    assert len(normalized.edges) == 18
    assert all(isinstance(edge.source, OutputReference) for edge in normalized.edges)
    assert all(edge.source.value_class == "ephemeral" for edge in normalized.edges)
    assert all(
        edge["source"]["value_class"] == "ephemeral"
        for edge in serialized["edges"]
    )
    assert all(
        output.can_materialize_as is None
        for operation_definition in normalized.operations
        for output in operation_definition.outputs
    )
    assert all(
        output["can_materialize_as"] is None
        for operation_definition in serialized["operations"]
        for output in operation_definition["outputs"]
    )
    assert all(
        output.reference.value_class == "ephemeral"
        for output in normalized.outputs
    )
    final_reference = next(
        output.reference for output in normalized.outputs if output.name == "evaluation"
    )
    assert final_reference.value_class == "ephemeral"
    serialized_final = next(
        output["reference"]
        for output in serialized["outputs"]
        if output["name"] == "evaluation"
    )
    assert serialized_final["value_class"] == "ephemeral"


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
    assert imported_roots == {"__future__", "hedloom_flow", "dataclasses"}
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
    with plan() as legacy_draft:
        with pytest.raises(TypeError):
            input_artifact("legacy-uri", "sidecar-base-directory")
    assert legacy_draft.finish(outputs={}).sources == ()

    with plan() as draft:
        base = input_artifact(
            address("repository-relative", "base"),
            artifact=artifact("sidecar-base-directory"),
            materialized_as=reference.REPOSITORY_DIRECTORY_TREE,
        )
        edits = input_artifact(
            address("repository-relative", "edits.py"),
            artifact=artifact("sidecar-edit-file"),
            materialized_as=reference.REPOSITORY_PYTHON_SOURCE,
        )
        with pytest.raises(BindingError, match="expects float"):
            reference.prepare_run.named("wrong-config")(
                base,
                edits,
                point_id="tt_1v80_27c",
                param_set="tt_1v80_27c",
                process="tt",
                vdd_v=1,
                temp_c=27,
            )
        with pytest.raises(BindingError, match="expects artifact kind"):
            reference.canonicalize_deck.named("wrong-kind")(
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
    locators = tuple(source.address.locator for source in normalized.sources)
    assert locators == tuple(source[0] for source in EXPECTED_SOURCES)
    assert all(
        not Path(locator).is_absolute() and ".." not in Path(locator).parts
        for locator in locators
    )
    assert all((ROOT / locator).exists() for locator in locators)

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
