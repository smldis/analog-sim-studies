"""ASS Run: walk a validated Plan and execute it.

The operator-facing half of a flow. It owns dependency order, readiness, and
value threading, and nothing else: attempts belong to `ass_exec`, the Plan to
`ass_flow`.
"""

from ass_run import driver as _driver
from ass_run.driver import *  # noqa: F401,F403

__all__ = [*_driver.__all__]
