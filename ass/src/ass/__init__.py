"""Author a study, inspect what it will do, and run it — from one import.

    from ass import operation, flow, plan, file, shell, lsf, Site, study

Everything here already existed in three units; what was missing was the seam
that let one file be a whole study. `ass_flow` still owns authoring and the
Plan, `ass_exec` still owns one attempt's durable record and imports neither
this package nor Dask, and `ass_run` still owns binding and readiness. This
package composes them and adds the one thing none of them could own alone: a
`submit` that runs what was authored, because it holds both halves.

The operation decorator here is `ass_flow`'s, wrapped so the body it already
kept is remembered as something callable. That is the whole difference. Before
it, `@operation` bodies were dead code and every study needed a second file to
supply real implementations — for the OTA reference, six hundred lines whose
only job was to agree with the first file.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from ass_flow import (  # noqa: F401 - the authoring surface, re-exported
    ArtifactContract,
    Parameter,
    Plan,
    Policy,
    ResourceContract,
    address,
    artifact,
    artifacts,
    codec,
    flow,
    input_artifact,
    local,
    materialization,
    named_policy,
    parameter,
    plan,
)
from ass_flow import operation as _operation
from ass_flow.authoring import file, returned, stdout, sweep  # noqa: F401
from ass_run.cluster import cluster_for, local_cluster  # noqa: F401
from ass_run.site import Site, SiteError  # noqa: F401

from ass.binding import BoundTransport, Shell, Workspace, shell  # noqa: F401
from ass.study import Study, StudyRun, submit  # noqa: F401

__all__ = [
    "ArtifactContract",
    "Parameter",
    "Plan",
    "Policy",
    "ResourceContract",
    "Shell",
    "Site",
    "SiteError",
    "Study",
    "StudyRun",
    "Workspace",
    "address",
    "artifact",
    "artifacts",
    "cluster_for",
    "codec",
    "file",
    "flow",
    "implementations",
    "input_artifact",
    "local",
    "local_cluster",
    "lsf",
    "materialization",
    "named_policy",
    "operation",
    "parameter",
    "plan",
    "returned",
    "shell",
    "stdout",
    "study",
    "submit",
    "sweep",
]

_IMPLEMENTATIONS: dict[str, Callable[..., Any]] = {}


def operation(
    function: Callable[..., Any] | None = None, **declaration: Any
) -> Any:
    """Declare an operation whose body is what actually runs.

    Identical to `ass_flow.operation` except that the decorated function is
    remembered here, keyed by the operation identity the Plan records. The Plan
    already carries that identity and a fingerprint of this source, so the
    registry resolves a name the document names — it does not smuggle in a
    second, unrecorded notion of what an operation is.
    """

    inner = _operation(**declaration)

    def decorate(body: Callable[..., Any]) -> Any:
        declared = inner(body)
        _IMPLEMENTATIONS[declared.identity.name] = body
        return declared

    # `@operation` bare, for a body that declares nothing but its signature.
    return decorate(function) if function is not None else decorate


def implementations() -> Mapping[str, Callable[..., Any]]:
    """Every operation body declared in this process."""

    return dict(_IMPLEMENTATIONS)


def lsf(**options: Any) -> Policy:
    """Place this work on its own LSF job, with its own resource request.

    Options travel to the job that needs them: `queue`, `cores`, `memory_mb`,
    `walltime`, a raw `resources` string, and `licences={"name": n}`, which
    becomes a `rusage` term so the scheduler that owns the licence count is the
    one that arbitrates it.
    """

    return named_policy("lsf")(**options)


def study(plan_object: Plan, *, implementations: Mapping[str, Any] | None = None) -> Study:
    """Pair a finished Plan with the bodies that implement it."""

    return Study(plan_object, implementations or _IMPLEMENTATIONS)
