"""Hedloom Run: walk a validated Plan and execute it.

The operator-facing half of a flow. It owns what a run *binds* — which
substrate provides a placement, which command implements an operation, which
address an upstream output landed at — and nothing else: attempts belong to
`hedloom_exec`, the Plan to `hedloom_flow`.

Readiness is a kernel rather than the unit. `run_plan` walks the plan in one
thread; `hedloom_run.graph.run_plan_graph` gives readiness to Dask. Both share the
binding rules in `hedloom_run.binding`, so the kernel decides how long a plan takes
and never what it means. The Dask kernel is an explicit import, so a plan small
enough to walk in one thread need not install a scheduler.
"""

from hedloom_run import driver as _driver
from hedloom_run.driver import *  # noqa: F401,F403

__all__ = [*_driver.__all__]
