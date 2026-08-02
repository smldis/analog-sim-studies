"""Named seams that the generic prototype deliberately leaves unresolved."""

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
        "real-operation-bindings",
        "Replace demonstration bindings with independently owned operations.",
        "How should ASS components expose callable operations without a global plugin framework?",
    ),
    DeferredCapability(
        "durable-reconciliation",
        "Reconstruct activity from manifests and scheduler observations.",
        "How should a closed client recover running, missing, or completed work?",
    ),
    DeferredCapability(
        "artifact-identity-staleness",
        "Identify every meaningful input and published artifact.",
        "Which code, data, environment, and configuration changes make work stale?",
    ),
    DeferredCapability(
        "evidence-promotion",
        "Separate completed operation outputs from accepted engineering evidence.",
        "Which validators and actors may promote an output?",
    ),
    DeferredCapability(
        "executor-routing",
        "Choose controller, direct batch, or Dask execution per invocation.",
        "When is a persistent worker inferior to one scheduler-visible job?",
    ),
    DeferredCapability(
        "policy-and-control",
        "Bound retries, cancellation, concurrency, scarce resources, and budgets.",
        "Which controls belong to authored policy versus an executor adapter?",
    ),
    DeferredCapability(
        "adaptive-planning",
        "Extend a flow after inspecting explicit evidence.",
        "How should new plan increments retain their decision history?",
    ),
    DeferredCapability(
        "operation-discovery",
        "Resolve stable operation identities across composed ASS components.",
        "When does direct Python binding become insufficient for discovery and versioning?",
    ),
)
