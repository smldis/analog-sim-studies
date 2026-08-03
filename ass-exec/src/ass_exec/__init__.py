"""ASS Exec: durable attempt identity, evidence, and reconciliation.

This unit owns exactly one thing: the lifecycle of a single attempt at a single
planned invocation, from an identity chosen before submission through terminal
reconciliation. It owns no graph, decides no readiness, and releases no
successors.

Work launched here is owner-bound: it is not meant to outlive the caller that
started it. The durable record therefore exists for evidence and for skipping
work that is already validly done, not for reattaching to work still running
from a previous life. Recording is declared per invocation rather than charged
to every call — see `ass_exec.durability`.
"""

from ass_exec import attempt as _attempt
from ass_exec import durability as _durability
from ass_exec import identity as _identity
from ass_exec import journal as _journal
from ass_exec import reuse as _reuse
from ass_exec import transport as _transport

from ass_exec.attempt import *  # noqa: F401,F403
from ass_exec.durability import *  # noqa: F401,F403
from ass_exec.identity import *  # noqa: F401,F403
from ass_exec.journal import *  # noqa: F401,F403
from ass_exec.reuse import *  # noqa: F401,F403
from ass_exec.transport import *  # noqa: F401,F403

__all__ = [
    *_identity.__all__,
    *_journal.__all__,
    *_reuse.__all__,
    *_transport.__all__,
    *_attempt.__all__,
    *_durability.__all__,
]
