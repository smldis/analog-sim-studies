from __future__ import annotations

import pytest


pytestmark = pytest.mark.skip(
    reason="TDD catalog for the proposed instance-net series source edit; not implemented yet."
)


def test_helper_shape_is_typed_and_traced() -> None:
    """One typed helper is exposed under sidecar_edits.edit.

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

    Chosen behavior:
    - Keep source_line as a single string.
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

    Chosen behavior:
    - Insert the source line before the modified instance.
    - Replace only the selected connected net token.
    - Preserve the rest of the instance text.
    """


def test_source_line_can_reference_original_net_internal_net_and_render_params() -> None:
    """source_line is formatted from render params and operation-local values.

    Example:

        COMMON_PARAMS = {"vdd": "1.2"}

        edit.insert_series_source_at_instance_net(
            path="input_main.scs",
            instance="X_SIDE_INJECT_001",
            net="in",
            internal_net="in__sidecar_inj",
            source_line="Vinj {net} {internal_net} PULSE(0 {vdd} ...)",
        )

    Expected source line:

        Vinj in in__sidecar_inj PULSE(0 1.2 ...)

    Chosen behavior:
    - {net} is the original selected net.
    - {internal_net} is the replacement net on the instance.
    - Normal render params are also available.
    """


def test_continuation_lines_are_preserved_while_replacing_selected_net() -> None:
    """The matched logical instance may span continuation lines.

    Input:

        X_SIDE_INJECT_001 in out
        + vss vdd amp

    Expected:

        Vinj_SIDE_INJECT_001 in in__sidecar_inj PULSE(...)
        X_SIDE_INJECT_001 in__sidecar_inj out
        + vss vdd amp

    Chosen behavior:
    - Extract the full logical instance including continuation lines.
    - Replace the selected net inside that selected text.
    - Avoid rebuilding or normalizing the instance when possible.
    """


def test_instance_parameters_are_preserved_as_unparsed_text() -> None:
    """Do not parse or rebuild params/subckt tokens for this first version.

    Input:

        X_SIDE_INJECT_001 in out vss vdd amp gain=10 m=2

    Expected:

        Vinj_SIDE_INJECT_001 in in__sidecar_inj PULSE(...)
        X_SIDE_INJECT_001 in__sidecar_inj out vss vdd amp gain=10 m=2

    Chosen behavior:
    - Treat the selected logical instance as text.
    - Replace only the selected net token.
    - Leave all other tokens and spacing unchanged where practical.
    """


def test_instance_line_comments_are_rejected() -> None:
    """Commented instance lines are out of scope for the first version.

    Inputs that should fail:

        X_SIDE_INJECT_001 in out vss vdd amp  $ comment
        X_SIDE_INJECT_001 in out vss vdd amp  ; comment
        X_SIDE_INJECT_001 in out vss vdd amp  * comment

    Chosen behavior:
    - If the selected logical instance contains '$', ';', or '*', fail.
    - Do not try to distinguish comment syntax from simulator-specific tokens yet.
    """


def test_missing_instance_fails_with_actionable_error() -> None:
    """Zero matches are a hard failure.

    Expected error should mention:
    - operation label through the renderer envelope,
    - instance name,
    - target file path.
    """


def test_duplicate_instance_name_fails_with_actionable_error() -> None:
    """More than one matching instance is a hard failure.

    Chosen behavior:
    - The feature relies on user-provided uniqueness.
    - No occurrence=... escape hatch in the first version.
    """


def test_selected_net_must_exist_on_instance() -> None:
    """If net is absent from the selected logical instance, fail.

    Expected error should include:
    - requested net,
    - instance name,
    - target file path.
    """


def test_selected_net_must_be_unique_on_instance() -> None:
    """Repeated selected net tokens are ambiguous.

    Input:

        X_SIDE_INJECT_001 in out vss vss amp

    If net="vss", fail with an error explaining that the selected net appears
    more than once on the instance.
    """


def test_instance_name_matching_supports_doubled_x_convention() -> None:
    """Some netlists may double the X prefix in instance text.

    Chosen behavior:
    - A request for instance="XFOO" may match "XFOO" or "XXFOO".
    - A request for instance="xfoo" may match case-insensitive equivalents.
    - If both accepted forms are present, fail as duplicate/ambiguous.
    """


def test_non_x_instance_is_rejected() -> None:
    """First version targets subckt instances only.

    Chosen behavior:
    - Require requested instance names to start with X/x.
    - Do not support arbitrary devices in this edit.
    """


def test_malformed_instance_text_is_out_of_scope_but_fails_cleanly() -> None:
    """Malformed selected instance text should not produce partial edits.

    This feature does not validate full SPICE syntax. It only needs enough
    structure to find one instance and one net token. If that cannot be done,
    fail before writing the file.
    """


def test_renderer_error_wraps_source_location() -> None:
    """Failures should use the existing traced edit envelope.

    Expected stderr shape:

        EDITS[1] insert_series_source_at_instance_net "..." failed
        created at edits.py:...
        reason: instance not found: X_SIDE_INJECT_001
    """

