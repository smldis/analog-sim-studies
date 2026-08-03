"""Direct LSF submission with owner-bound job lifetime.

One selected invocation becomes one `bsub -I` job with its own job name,
resource request, and exit status. Interactive submission is the mechanism, not
a concession to human use: LSF ties the job's life to the submitting client, so
the job cannot outlive the work that wanted it. Nothing here maintains a lease,
a heartbeat, or a reaper.

The client is a child of this process, which leaves one gap: if this process is
killed outright, the child would ordinarily be reparented and keep its job
alive. Two local mechanisms close it — the child stays in our process group, so
a group signal reaches it, and on Linux it asks the kernel to signal it when
its parent dies. Neither involves LSF.

This mode holds one process and one connection per concurrent job, which is
right for a handful of independently visible jobs and wrong for hundreds. Many
similar jobs belong on a pooled `LSFCluster` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence
import os
import shlex
import signal
import subprocess
import sys

from ass_exec.transport import Observation, SubmissionRefused, TransportError

__all__ = [
    "CommandResult",
    "LSFInteractiveTransport",
    "LSFPooledTransport",
    "SubprocessRunner",
]


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _bind_child_lifetime() -> Callable[[], None] | None:
    """Ask the kernel to signal our children when we die.

    Linux only. Combined with the child staying in our process group, this is
    what makes "the job dies with its owner" true even when the owner is killed
    without a chance to clean up.
    """

    if sys.platform != "linux":
        return None

    def preexec() -> None:  # pragma: no cover - runs in the forked child
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        PR_SET_PDEATHSIG = 1
        libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)

    return preexec


class SubprocessRunner:
    """Run a command as a child bound to this process's lifetime."""

    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        merged = dict(os.environ)
        if env:
            merged.update(env)
        try:
            completed = subprocess.run(
                list(argv),
                cwd=cwd,
                env=merged,
                capture_output=True,
                text=True,
                timeout=timeout,
                # Deliberately not start_new_session: staying in the caller's
                # process group is half of the owner-bound guarantee.
                preexec_fn=_bind_child_lifetime(),
            )
        except FileNotFoundError as error:
            raise SubmissionRefused(f"{argv[0]!r} is not available") from error
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )


class LSFInteractiveTransport:
    """One `bsub -I` job per attempt, bound to this process's lifetime."""

    name = "lsf-interactive"
    # The site supports lookup by job name, so a negative answer is trustworthy.
    discovery_is_authoritative = True

    def __init__(
        self,
        *,
        walltime: str,
        queue: str | None = None,
        resources: str | None = None,
        cores: int | None = None,
        runner: Callable[..., CommandResult] | None = None,
    ) -> None:
        if not walltime:
            raise ValueError(
                "walltime is required: it is the only orphan bound that "
                "survives this process being killed without warning"
            )
        self.walltime = walltime
        self.queue = queue
        self.resources = resources
        self.cores = cores
        self._run = runner or SubprocessRunner()

    def build_argv(self, identity: str, bundle: Mapping[str, Any]) -> list[str]:
        command = bundle.get("command")
        if not command or not isinstance(command, (list, tuple)):
            raise SubmissionRefused(
                "an LSF bundle needs a 'command' list; external work is a "
                "command line, not an in-process callable"
            )
        argv = ["bsub", "-I", "-J", identity, "-W", self.walltime]
        if self.queue:
            argv += ["-q", self.queue]
        if self.cores:
            argv += ["-n", str(self.cores)]
        if self.resources:
            argv += ["-R", self.resources]
        return argv + list(command)

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        """Submit and wait. With `-I` the call returns when the job is over."""

        argv = self.build_argv(identity, bundle)
        result = self._run(
            argv, cwd=bundle.get("cwd"), env=bundle.get("env")
        )
        self._last = {
            "transport": self.name,
            "identity": identity,
            "command": shlex.join(argv),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        return dict(self._last)

    def discover(self, identity: str) -> Mapping[str, Any] | None:
        """Ask LSF whether a job with this name is still around.

        With owner-bound lifetime a match should be rare; it means a previous
        run left something behind. The caller decides what to do about it.
        """

        result = self._run(["bjobs", "-J", identity, "-noheader"])
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return {
            "transport": self.name,
            "identity": identity,
            "observed": result.stdout.strip(),
        }

    def poll(self, handle: Mapping[str, Any]) -> Observation:
        returncode = handle.get("returncode")
        if returncode is None:
            return Observation("absent")
        if returncode == 0:
            return Observation("succeeded", {"stdout": handle.get("stdout", "")})
        return Observation(
            "failed",
            {
                "returncode": returncode,
                "stderr": handle.get("stderr", ""),
            },
        )

    def cancel(self, handle: Mapping[str, Any]) -> None:
        identity = handle.get("identity")
        if not identity:
            raise TransportError("cannot cancel an attempt with no identity")
        self._run(["bkill", "-J", identity])


class LSFPooledTransport:
    """Refusing boundary for pooled execution over reusable LSF workers.

    Many similar invocations belong on a `dask_jobqueue.LSFCluster`, whose
    workers already die with their scheduler via `death_timeout` and are
    `bkill`ed on cluster close. That is the same owner-bound property this unit
    wants, already implemented and exercised elsewhere, so it should be adopted
    rather than rebuilt. Nothing is implemented here yet.
    """

    name = "lsf-pooled"
    discovery_is_authoritative = False

    def _refuse(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "pooled LSF execution is not implemented. It should adopt "
            "dask_jobqueue.LSFCluster rather than reimplement worker "
            "lifetime; use LSFInteractiveTransport for individually visible "
            "jobs in the meantime."
        )

    submit = discover = poll = cancel = _refuse
