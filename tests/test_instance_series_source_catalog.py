from __future__ import annotations

import pytest


pytestmark = pytest.mark.skip(
    reason="TDD catalog for the proposed instance-net series source edit; not implemented yet."
)


def test_helper_shape_is_typed_and_traced() -> None:
    """Chosen API shape: one typed helper under sidecar_edits.edit.

    Proposed call:

        edit.insert_series_source_at_instance_net(
            path="input_main.scs",
            instance="X_SIDE_INJECT_001",
            net="in",
            internal_net="in__sidecar_inj",
            source_line=(
                "Vinj_SIDE_INJECT_001 {net} {internal_net} "
                "PULSE(0 1.2 0 10p 10p 4n 8n)"
            ),
            description="inject pulse on unique instance input",
        )

    Implementation choice:
    - Keep the public model consistent with the current typed edit objects.
    - Capture source_stack at construction time.
    - Do not introduce custom edit specs or generic field bags.
    """


def test_simple_instance_line_inserts_source_before_instance() -> None:
    """Happy path for one-line X instance.

    Input:

        X_SIDE_INJECT_001 in out vss vdd amp

    Expected:

        Vinj_SIDE_INJECT_001 in in__sidecar_inj PULSE(0 1.2 0 10p 10p 4n 8n)
        X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp

    Implementation choice:
    - Insert the source before the modified instance.
    - Replace only the selected connected net token.
    - Preserve the instance name and original subckt/model token.
    """


def test_source_line_can_reference_original_net_and_internal_net() -> None:
    """source_line should be a small template evaluated after the instance is found.

    Template variables chosen for first version:
    - {net}: the original connected net selected by the user.
    - {internal_net}: the replacement net used on the instance pin.

    Alternative to evaluate:
    - Add {instance} for source naming convenience.
    - Add {source_name} as a separate field instead of making users format it.
    """


def test_path_and_user_source_line_still_use_render_params() -> None:
    """The edit must compose with existing render params.

    Example:

        path="runs/{corner}/input.scs"
        source_line="Vinj {net} {internal_net} PULSE(0 {vdd} ...)"

    Implementation choice:
    - First apply normal render params.
    - Then apply operation-local values such as net/internal_net.

    Alternative to evaluate:
    - Reverse formatting order. This is likely worse because render params could
      accidentally consume operation-local names.
    """


def test_continuation_lines_are_treated_as_one_logical_instance() -> None:
    """Support common SPICE continuation syntax.

    Input:

        X_SIDE_INJECT_001 in out
        + vss vdd amp

    Expected:

        Vinj_SIDE_INJECT_001 in in__sidecar_inj PULSE(...)
        X_SIDE_INJECT_001 in__sidecar_inj out
        + vss vdd amp

    Implementation choice to make:
    - Option A: preserve continuation shape when rewriting.
    - Option B: collapse the instance to one logical line.

    Recommendation:
    - Start with Option B if preserving layout is too costly, but document it.
    - Prefer Option A only if it stays simple.
    """


def test_instance_params_are_preserved_after_subckt_name() -> None:
    """The scanner must distinguish pins from params.

    Input:

        X_SIDE_INJECT_001 in out vss vdd amp gain=10 m=2

    Expected:

        Vinj_SIDE_INJECT_001 in in__sidecar_inj PULSE(...)
        X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp gain=10 m=2

    Implementation choice:
    - For first version, infer params as tokens after the subckt/model token.
    - If any token has key=value, use the token before the first key=value as
      the subckt/model name.
    - If no key=value exists, use the last token as the subckt/model name.
    """


def test_inline_comment_is_preserved() -> None:
    """Inline comments should not become part of pins or params.

    Input:

        X_SIDE_INJECT_001 in out vss vdd amp  $ injected candidate

    Expected:

        Vinj_SIDE_INJECT_001 in in__sidecar_inj PULSE(...)
        X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp  $ injected candidate

    Implementation choices to evaluate:
    - Support '$' inline comments first.
    - Decide whether ';' comments or simulator-specific comments matter.
    - Avoid treating comment text as connection tokens.
    """


def test_missing_instance_fails_with_actionable_error() -> None:
    """Zero matches should be a hard failure.

    Expected error should mention:
    - operation label through the renderer envelope,
    - instance name,
    - target file path.
    """


def test_duplicate_instance_name_fails_with_actionable_error() -> None:
    """More than one matching instance should be a hard failure.

    Rationale:
    - The feature relies on user-provided uniqueness.
    - Guessing would silently modify the wrong device.

    Alternative to evaluate later:
    - Accept occurrence=... as an escape hatch.
    """


def test_selected_net_must_exist_on_instance() -> None:
    """If net is absent, fail and show available connection nets.

    Error should include:
    - requested net,
    - instance name,
    - available nets before replacement.
    """


def test_selected_net_must_be_unique_on_instance_by_default() -> None:
    """Repeated connected nets are ambiguous.

    Input:

        X_SIDE_INJECT_001 in out vss vss amp

    If net="vss", first version should fail.

    Alternative to evaluate later:
    - net_occurrence=1 based on connection-token occurrence.
    - pin_name=... if we later add subckt interface lookup.
    """


def test_internal_net_must_not_already_be_connected_to_same_instance() -> None:
    """Avoid generating a no-op or confusing rewrite.

    Input:

        X_SIDE_INJECT_001 in in__sidecar_inj vss vdd amp

    If internal_net="in__sidecar_inj", fail before rewriting.

    Alternative:
    - Allow it because the source may still be meaningful.
    - Safer first version is to reject.
    """


def test_instance_name_matching_is_token_based_not_substring_based() -> None:
    """Avoid accidental matches.

    Searching for XU1 must not match:
    - XU10
    - XXU1
    - comments mentioning XU1

    Implementation choice:
    - Use a line/logical-statement regex with instance-name token boundary.
    """


def test_non_x_instance_is_rejected_or_deferred() -> None:
    """First version should target subckt instances only.

    Chosen constraint:
    - Require instance names starting with X/x.

    Alternative to evaluate:
    - Support arbitrary devices later, but then model/name and pin parsing become
      device-class specific.
    """


def test_missing_or_ambiguous_subckt_model_token_fails() -> None:
    """The scanner must be able to split pins from the referenced subckt/model.

    Failure examples:
    - "X_SIDE_INJECT_001 in"
    - malformed continuation that drops the subckt token
    - params without a clear subckt token
    """


def test_renderer_error_wraps_source_location() -> None:
    """Failures should use the existing traced edit envelope.

    Expected stderr shape:

        EDITS[1] insert_series_source_at_instance_net "..." failed
        created at edits.py:...
        reason: instance not found: X_SIDE_INJECT_001
    """


def test_dynamic_generation_of_many_injections_remains_ergonomic() -> None:
    """The feature should work with generated edit lists.

    Example:

        EDITS = [
            edit.insert_series_source_at_instance_net(
                path="input_main.scs",
                instance=f"X_SIDE_INJECT_{idx}",
                net=row["net"],
                internal_net=f"{row['net']}__inj_{idx}",
                source_line=row["source_line"],
            )
            for idx, row in enumerate(rows)
        ]

    Error reporting should rely on EDITS[index] plus source_stack, as today.
    """


def test_interaction_with_write_file_and_append_file_for_generated_sources() -> None:
    """Decide whether source_line is enough or source definitions can be external.

    Current preferred model:
    - source_line is inserted directly next to the instance.

    Alternative:
    - write_file generates source include content and this edit only rewires the
      instance. That is less direct and may not work because the source must sit
      electrically in series at the same hierarchy level.
    """


def test_layout_preservation_policy_is_explicit() -> None:
    """We need to choose how much formatting to preserve.

    Option A:
    - Preserve original indentation and inline comments.
    - Collapse continuation lines only if necessary.

    Option B:
    - Normalize the rewritten logical instance to a single line.
    - Simpler and likely acceptable for generated run directories.

    Recommendation:
    - Preserve indentation/comment, allow line normalization in first version.
    """

