"""Named seams that the prototype deliberately leaves unresolved."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeferredCapability:
    """A future question, not an implemented or promised contract."""

    capability_id: str
    seam: str
    question: str


DEFERRED_CAPABILITIES = (
    DeferredCapability(
        "real-operation-adapters",
        "Replace simulation and measurement placeholders.",
        "How should Sidecar, simulators, parsers, and CACE-shaped operations bind?",
    ),
    DeferredCapability(
        "durable-reconciliation",
        "Reconstruct activity from manifests and scheduler observations.",
        "How should a closed client recover running, missing, or completed work?",
    ),
    DeferredCapability(
        "artifact-identity-staleness",
        "Identify every meaningful input and published artifact.",
        "Which code, PDK, model, environment, and configuration changes stale work?",
    ),
    DeferredCapability(
        "evidence-promotion",
        "Separate completed attempts from accepted engineering evidence.",
        "Which validators and actors may promote a result?",
    ),
    DeferredCapability(
        "executor-routing",
        "Choose local, direct LSF, or Dask execution per invocation.",
        "When is a persistent Dask worker inferior to one visible LSF job?",
    ),
    DeferredCapability(
        "policy-and-control",
        "Bound retries, cancellation, concurrency, licences, and budgets.",
        "Which controls belong to authored policy versus an executor adapter?",
    ),
    DeferredCapability(
        "adaptive-planning",
        "Extend a study after inspecting explicit evidence.",
        "How should new plan increments retain their decision history?",
    ),
    DeferredCapability(
        "domain-profiles",
        "Add analog and CACE vocabulary without narrowing the generic envelope.",
        "Which fields belong in StudySpec and which in a characterization profile?",
    ),
)
