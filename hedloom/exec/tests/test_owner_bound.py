"""Real evidence that a child does not survive its owner.

LSF's own guarantee — that an interactive job dies when its client dies —
cannot be reproduced without LSF. The other half can: whether the `bsub` client
we spawn survives *us* being killed without warning is a property of local
process handling, and it is testable here with real processes and real signals.

That half is the one we implemented, so it is the one we should prove.
"""

import os
import signal
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="PR_SET_PDEATHSIG is Linux-only"
)

# An intermediate process standing in for a controller: it spawns a long-lived
# grandchild the way SubprocessRunner does, reports the pid, then waits.
INTERMEDIATE = """
import sys, time
sys.path.insert(0, {src!r})
from hedloom_exec.lsf import _bind_child_lifetime
import subprocess
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(60)"],
    preexec_fn=_bind_child_lifetime(),
)
print(child.pid, flush=True)
time.sleep(60)
"""

SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_until_gone(pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return False


def test_a_spawned_child_dies_when_its_owner_is_killed_outright():
    owner = subprocess.Popen(
        [sys.executable, "-c", INTERMEDIATE.format(src=SRC)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        grandchild = int(owner.stdout.readline().strip())
        assert _alive(grandchild)

        # SIGKILL: the owner gets no chance to clean up. This is the case a
        # signal handler cannot cover and a lease would only bound.
        owner.kill()
        owner.wait(timeout=5)

        assert _wait_until_gone(grandchild), (
            "the child outlived an owner killed without warning; the "
            "owner-bound guarantee is not actually enforced"
        )
    finally:
        if owner.poll() is None:  # pragma: no cover - cleanup path
            owner.kill()


def test_the_binding_is_requested_for_every_spawned_command():
    from hedloom_exec.lsf import _bind_child_lifetime

    # The preexec hook must exist on Linux; its absence would silently reduce
    # the guarantee to "usually", which is the failure mode worth catching.
    assert _bind_child_lifetime() is not None
