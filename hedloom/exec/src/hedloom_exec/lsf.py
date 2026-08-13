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

The cost of one job per invocation is queue dispatch latency, paid once per
job. For work that runs for minutes it disappears into the noise; for a
two-second step it dwarfs the work itself. The axis is therefore how long an
invocation runs, not how many there are: a thousand ten-minute corners are a
fine fit, a hundred two-second extractions are not, and those belong on a
pooled `LSFCluster` that pays dispatch once per worker.

What a job asks for is decided per invocation, not per transport. The Plan
resolves a placement and its options — queue, cores, memory, and the logical
scarce resources an analog sweep really contends for, simulator licences — and
those become `-q`, `-n`, and `rusage` on that job alone. Licences are handed to
LSF rather than counted here on purpose: the scheduler is the only party that
knows how many exist and which other users hold them, so arbitration belongs to
it. This unit's job is to state the need on the specific job that has it.

Concurrency has a separate, softer cost: each *simultaneously running* job holds
a blocked client process and connection on the submit host. That scales with the
concurrency limit rather than the job count, and its real ceiling is site policy
— per-user process limits, maximum pending jobs — which this unit does not know
and should not guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence
import os
import re
import shlex
import signal
import subprocess
import sys

from hedloom_exec.transport import (
    Observation,
    SubmissionRefused,
    TransportError,
    placement_options,
)


class CommandUnavailable(TransportError):
    """A required LSF command is not on PATH.

    Indeterminate by default. Only the caller that was about to *submit* may
    read it as a refusal; a missing `bjobs` says nothing about whether work was
    accepted, and must never be reported as one.
    """

__all__ = [
    "CommandResult",
    "CommandUnavailable",
    "JobSettings",
    "LSFInteractiveTransport",
    "LSFPooledTransport",
    "PLACEMENT_OPTIONS",
    "SubprocessRunner",
]


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


_PR_SET_PDEATHSIG = 1


def _load_libc():
    """Load libc once, at import, in the parent.

    Deliberately not inside `preexec_fn`: that runs between fork and exec,
    where only async-signal-safe calls are legal, and `CDLL` performs a dlopen
    that takes the loader lock. If another thread held that lock at fork time
    the child would hang forever, with the submitting thread blocked in
    `subprocess.run`.
    """

    if sys.platform != "linux":
        return None
    try:
        import ctypes

        return ctypes.CDLL("libc.so.6", use_errno=True)
    except OSError:  # pragma: no cover - unusual libc layout
        return None


_LIBC = _load_libc()


def _bind_child_lifetime() -> Callable[[], None] | None:
    """Ask the kernel to signal our children when we die.

    Linux only. Combined with the child staying in our process group, this is
    what makes "the job dies with its owner" true even when the owner is killed
    without a chance to clean up.
    """

    if _LIBC is None:
        return None

    def preexec() -> None:  # pragma: no cover - runs in the forked child
        # Failure must be loud. A silently unset PDEATHSIG degrades the
        # owner-bound guarantee to "usually", and the orphan it leaves is an
        # LSF job nobody is watching.
        if _LIBC.prctl(_PR_SET_PDEATHSIG, signal.SIGTERM) != 0:
            os._exit(127)

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
            raise CommandUnavailable(f"{argv[0]!r} is not available") from error
        except subprocess.TimeoutExpired as error:
            # subprocess.run has already killed the client, and with `-I` that
            # takes the job with it. Indeterminate rather than refused: the job
            # may have run, or even completed, before we stopped waiting.
            raise TransportError(
                f"{argv[0]} exceeded its {timeout}s bound and was killed"
            ) from error
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )


_SUBMISSION_ERROR_RETURNCODE = 255
_NOT_FOUND_MARKERS = ("is not found", "No unfinished job found", "not found")
_REJECTION_MARKERS = (
    "Job not submitted",
    "Bad queue name",
    "Illegal option",
    "User cannot use the queue",
    "Too many jobs",
    "Bad resource requirement",
)


def _is_submission_rejection(result: CommandResult) -> bool:
    """Whether bsub refused the job rather than running it.

    LSF reports submission errors with exit 255 and an explanatory message.
    A payload that itself exits 255 is indistinguishable by exit code alone,
    so a recognised rejection message is required as well — the ambiguity is
    resolved toward "the work ran", because wrongly refusing a real result is
    worse than one extra rerun.
    """

    if result.returncode != _SUBMISSION_ERROR_RETURNCODE:
        return False
    return any(marker in result.stderr for marker in _REJECTION_MARKERS)


def _is_not_found(result: CommandResult) -> bool:
    """Whether bjobs answered "no such job" rather than failing to answer."""

    text = f"{result.stdout} {result.stderr}"
    return any(marker in text for marker in _NOT_FOUND_MARKERS)


def _state_from_bjobs(line: str) -> str:
    """Map an LSF status word onto an observed state."""

    tokens = line.split()
    for token in tokens:
        if token in ("PEND", "PSUSP", "WAIT"):
            return "pending"
        if token in ("RUN", "USUSP", "SSUSP"):
            return "running"
        if token == "DONE":
            return "succeeded"
        if token in ("EXIT", "ZOMBI"):
            return "failed"
    return "running"


PLACEMENT_OPTIONS = (
    "cores",
    "licences",
    "memory_mb",
    "queue",
    "resources",
    "walltime",
)
"""The placement vocabulary this transport can express as `bsub` arguments.

Closed deliberately. An option outside it is refused rather than ignored: an
author who writes `queeu="bigmem"` or asks for something only a pooled
placement provides has stated a resource need, and running the work without it
is the silent-wrongness this project treats as a defect. The refusal happens
before `bsub` is called, so nothing was accepted.
"""

_RESOURCE_NAME = re.compile(r"\A[A-Za-z_][A-Za-z0-9_.-]*\Z")


@dataclass(frozen=True, slots=True)
class JobSettings:
    """What one invocation actually asks LSF for.

    Resolved per submission from the transport's site defaults and the
    invocation's own placement options, the latter winning. Recorded on the
    handle so the published manifest can answer "what did this job request?"
    without reparsing a command line.
    """

    walltime: str
    queue: str | None = None
    cores: int | None = None
    memory_mb: int | None = None
    licences: Mapping[str, int] = field(default_factory=dict)
    resources: str | None = None

    def as_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"walltime": self.walltime}
        for key in ("queue", "cores", "memory_mb", "resources"):
            value = getattr(self, key)
            if value is not None:
                data[key] = value
        if self.licences:
            data["licences"] = dict(self.licences)
        return data


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SubmissionRefused(
            f"placement option {label} must be a positive integer, got {value!r}"
        )
    return value


def _walltime(value: object) -> str:
    """`-W` is the one orphan bound that survives everything else failing."""

    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise SubmissionRefused(
            f"placement option walltime must be a non-empty LSF duration, got "
            f"{value!r}; without it a lost owner leaves a job nobody bounds"
        )
    return value


def _licences(value: object) -> dict[str, int]:
    """A declared need for a scarce resource LSF, not this unit, arbitrates."""

    if not isinstance(value, Mapping):
        raise SubmissionRefused(
            f"placement option licences must be a mapping of resource name to "
            f"count, got {type(value).__name__}"
        )
    resolved: dict[str, int] = {}
    for name, count in value.items():
        if not isinstance(name, str) or not _RESOURCE_NAME.match(name):
            raise SubmissionRefused(
                f"licence {name!r} is not a usable LSF resource name; it has to "
                "be the name the site's LSF configuration already knows"
            )
        resolved[name] = _positive_int(count, f"licences[{name}]")
    return resolved


def _rusage(settings: JobSettings) -> str | None:
    """Compose one `rusage` section, sorted so the same request renders alike."""

    terms = []
    if settings.memory_mb is not None:
        terms.append(f"mem={settings.memory_mb}")
    terms += [
        f"{name}={count}" for name, count in sorted(settings.licences.items())
    ]
    return f"rusage[{','.join(terms)}]" if terms else None


def _resource_arguments(settings: JobSettings) -> list[str]:
    """Render the resource requirement as a single `-R` string.

    LSF's requirement grammar is a sequence of whitespace-separated sections —
    `select[...] rusage[...] span[...]` — so a site default like
    `span[hosts=1]` and a composed `rusage[...]` combine into one argument.
    What is *not* safe is merging two `rusage` sections: their semantics are
    per-resource and we would be guessing. That case refuses.

    Unverified against a real farm, like everything else here; the preflight
    script checks it where it can be checked.
    """

    rusage = _rusage(settings)
    raw = settings.resources
    if rusage is None:
        return ["-R", raw] if raw else []
    if raw is None:
        return ["-R", rusage]
    if "rusage" in raw:
        raise SubmissionRefused(
            f"cannot merge the composed {rusage} into the resource string "
            f"{raw!r}, which already has a rusage section. Declare memory and "
            "licences one way or the other, not both."
        )
    return ["-R", f"{raw} {rusage}"]


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
        timeout: float | None = None,
        runner: Callable[..., CommandResult] | None = None,
    ) -> None:
        if not walltime:
            raise ValueError(
                "walltime is required: it is the only orphan bound that "
                "survives this process being killed without warning"
            )
        # Site defaults for invocations that declare nothing of their own. A
        # plan that authors placement options overrides them per invocation.
        self.walltime = walltime
        self.queue = queue
        self.resources = resources
        self.cores = cores
        # Bounds our own wait. `-W` bounds the job on the farm, but nothing
        # stopped a hung client from blocking its caller indefinitely.
        self.timeout = timeout
        self._run = runner or SubprocessRunner()

    def settings_for(self, bundle: Mapping[str, Any]) -> JobSettings:
        """Resolve this invocation's request over the transport's defaults.

        The Plan decided per invocation which queue, how many cores, and which
        scarce resources this work needs. Those must reach the job that runs it:
        a corner sized for a large-memory queue is a different experiment when
        it lands wherever the transport was constructed to point.
        """

        options = dict(placement_options(bundle))
        unknown = sorted(set(options) - set(PLACEMENT_OPTIONS))
        if unknown:
            raise SubmissionRefused(
                f"placement asked for {', '.join(unknown)}, which this transport "
                f"cannot express as bsub arguments (it understands "
                f"{', '.join(PLACEMENT_OPTIONS)}). Ignoring a stated resource "
                "need would run the work under conditions nobody asked for."
            )

        cores = options.get("cores", self.cores)
        memory = options.get("memory_mb")
        queue = options.get("queue", self.queue)
        resources = options.get("resources", self.resources)
        if queue is not None and (not isinstance(queue, str) or not queue.strip()):
            raise SubmissionRefused(
                f"placement option queue must be a queue name, got {queue!r}"
            )
        if resources is not None and not isinstance(resources, str):
            raise SubmissionRefused(
                "placement option resources must be an LSF requirement string"
            )

        return JobSettings(
            walltime=_walltime(options.get("walltime", self.walltime)),
            queue=queue,
            cores=None if cores is None else _positive_int(cores, "cores"),
            memory_mb=None if memory is None else _positive_int(memory, "memory_mb"),
            licences=_licences(options.get("licences", {})),
            resources=resources,
        )

    def build_argv(
        self,
        identity: str,
        bundle: Mapping[str, Any],
        settings: JobSettings | None = None,
    ) -> list[str]:
        command = bundle.get("command")
        if not command or not isinstance(command, (list, tuple)):
            raise SubmissionRefused(
                "an LSF bundle needs a 'command' list; external work is a "
                "command line, not an in-process callable"
            )
        settings = settings or self.settings_for(bundle)
        argv = ["bsub", "-I", "-J", identity, "-W", settings.walltime]
        if settings.queue:
            argv += ["-q", settings.queue]
        if settings.cores:
            argv += ["-n", str(settings.cores)]
        argv += _resource_arguments(settings)
        return argv + list(command)

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        """Submit and wait. With `-I` the call returns when the job is over.

        A `bsub` that rejects the submission must not be recorded as the work
        failing: nothing ran, so the outcome belongs to the submission, not to
        the payload. Recording it as a failure would publish a terminal result
        for work that never started.
        """

        settings = self.settings_for(bundle)
        argv = self.build_argv(identity, bundle, settings)
        workdir = bundle.get("workdir") or bundle.get("cwd")
        try:
            result = self._run(
                argv, cwd=workdir, env=bundle.get("env"), timeout=self.timeout
            )
        except CommandUnavailable as error:
            # No bsub means nothing was accepted; this one really is a refusal.
            raise SubmissionRefused(str(error)) from error

        if _is_submission_rejection(result):
            raise SubmissionRefused(
                f"bsub rejected the submission (rc={result.returncode}): "
                f"{result.stderr.strip()[:200]}"
            )

        return {
            "transport": self.name,
            "identity": identity,
            "kind": "completed",
            "workdir": workdir,
            # What this job asked LSF for, as data rather than as a parsed
            # command line: the record should be able to explain a slow or
            # licence-starved run without re-deriving the request.
            "settings": settings.as_data(),
            "command": shlex.join(argv),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def discover(self, identity: str) -> Mapping[str, Any] | None:
        """Ask LSF whether a job with this name is still around.

        With owner-bound lifetime a match should be rare; it means a previous
        run left something behind. A handle returned here describes a job that
        is still *live* on the farm, which is a different thing from the
        finished-job handle `submit` returns — `kind` distinguishes them so
        `poll` cannot confuse the two.
        """

        try:
            result = self._run(["bjobs", "-J", identity, "-noheader"])
        except CommandUnavailable:
            # We cannot ask. That is not the same as "nothing was accepted",
            # and answering None here would licence a duplicate submission.
            raise

        if result.returncode == 0 and result.stdout.strip():
            return {
                "transport": self.name,
                "identity": identity,
                "kind": "live",
                "observed": result.stdout.strip(),
            }
        if _is_not_found(result):
            return None
        raise TransportError(
            f"bjobs could not answer for {identity} (rc={result.returncode}): "
            f"{result.stderr.strip()[:200]}"
        )

    def poll(self, handle: Mapping[str, Any]) -> Observation:
        """Read the state of a handle, whichever kind it is."""

        if handle.get("kind") == "completed" or "returncode" in handle:
            returncode = handle["returncode"]
            if returncode == 0:
                return Observation("succeeded", {"stdout": handle.get("stdout", "")})
            return Observation(
                "failed",
                {"returncode": returncode, "stderr": handle.get("stderr", "")},
            )

        # A live handle describes a job we attached to rather than ran, so its
        # state has to be asked for. Reporting `absent` without asking is what
        # published a running job as unreconciled.
        identity = handle.get("identity")
        if not identity:
            raise TransportError("cannot poll a handle with no identity")
        found = self.discover(identity)
        if found is None:
            return Observation("absent")
        return Observation(_state_from_bjobs(found["observed"]), {"observed": found["observed"]})

    def cancel(self, handle: Mapping[str, Any]) -> None:
        identity = handle.get("identity")
        if not identity:
            raise TransportError("cannot cancel an attempt with no identity")
        # A missing bkill is indeterminate, never a refusal: cancel intent has
        # already been recorded and the job may well be running.
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
