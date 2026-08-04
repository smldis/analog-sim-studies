"""Running the bodies a Plan names.

Until now an operation body was dead code: `@operation` kept the function and
nothing ever called it, so every study needed a second file supplying real
implementations, command lines, and output paths — for the OTA reference, six
hundred lines of them. The Plan could say what it meant and not what it would
do.

This module closes that. A bound transport takes the operations a study
authored, and when the executor asks it to run an invocation it calls the body
with the inputs the Plan resolved and an `out` namespace addressing that
attempt's own workspace.

The invariant:

    A body decides what runs; it never decides *whether* it runs.

Reuse, identity, ordering and placement are settled before a body is called,
so an author cannot accidentally acquire scheduling authority by writing
Python. A body that returns a `Shell` is a launcher: the command it built is
handed to the substrate its placement names, which is how one corner becomes
one `bsub -I` job while the launcher itself costs nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import shlex

from ass_exec.transport import Observation, SubmissionRefused, Transport

__all__ = ["BoundTransport", "Shell", "Workspace", "shell"]


@dataclass(frozen=True, slots=True)
class Shell:
    """A command an operation wants run, rather than one it ran itself.

    Returning this instead of calling a subprocess is what lets the command
    reach a placement: the body builds argv cheaply wherever it runs, and the
    substrate — a local process, or one `bsub -I` job with this corner's queue,
    cores and licence — executes it.
    """

    argv: tuple[str, ...]

    def __str__(self) -> str:
        return shlex.join(self.argv)


def shell(*argv: Any) -> Shell:
    """Build the command this operation wants run at its placement."""

    if not argv:
        raise SubmissionRefused("shell() needs a command")
    return Shell(tuple(str(item) for item in argv))


class Workspace:
    """The declared outputs of one attempt, as paths inside its own directory.

    An operation writes to `out.<name>`, which is where the executor will
    afterwards look for that declared output. The two cannot drift apart,
    because they are the same declaration read once.
    """

    def __init__(self, directory: str | Path, bindings: Mapping[str, Mapping[str, Any]]):
        self.directory = Path(directory)
        self._bindings = dict(bindings)

    def __getattr__(self, name: str) -> Path:
        binding = self._bindings.get(name)
        if binding is None or "path" not in binding:
            raise AttributeError(
                f"this operation declares no file output named {name!r} "
                f"(declares: {', '.join(sorted(self._bindings)) or 'none'})"
            )
        return self.directory / binding["path"]

    def __repr__(self) -> str:  # pragma: no cover - diagnostics
        return f"Workspace({self.directory}, {sorted(self._bindings)})"


class BoundTransport:
    """Calls the authored body, then delegates whatever it asks for.

    Wraps the substrate a placement names. A body returning a value has done
    its work in process and the value is the result; a body returning a
    `Shell` has built a command, which the delegate submits. From the
    executor's side this is an ordinary transport, so identity, the journal,
    reuse and reconciliation are untouched.
    """

    discovery_is_authoritative = True

    def __init__(
        self,
        implementations: Mapping[str, Callable[..., Any]],
        delegate: Transport | None = None,
    ) -> None:
        self._implementations = dict(implementations)
        self._delegate = delegate
        self._results: dict[str, Observation] = {}
        self.name = f"bound:{delegate.name}" if delegate is not None else "bound"
        if delegate is not None:
            self.discovery_is_authoritative = delegate.discovery_is_authoritative

    def _call(self, bundle: Mapping[str, Any]) -> Any:
        operation = bundle.get("operation")
        implementation = self._implementations.get(operation)
        if implementation is None:
            # Established before anything could run: a genuine refusal.
            raise SubmissionRefused(
                f"no implementation is bound for operation {operation!r}"
            )
        arguments = dict(bundle.get("arguments", {}))
        # Resolved upstream values are execution detail, never identity.
        arguments.update(bundle.get("resolved_inputs", {}))
        workdir = bundle.get("workdir")
        if workdir is not None and _wants_workspace(implementation):
            arguments["out"] = Workspace(workdir, bundle.get("outputs") or {})
        return implementation(**arguments)

    def submit(self, identity: str, bundle: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            produced = self._call(bundle)
        except SubmissionRefused:
            raise
        except Exception as error:  # deliberate: failure is a recordable outcome
            self._results[identity] = Observation(
                "failed", {"error": f"{type(error).__name__}: {error}"}
            )
            return _local_handle(self.name, identity, bundle)

        if isinstance(produced, Shell):
            if self._delegate is None:
                # A local placement runs the command here. The runner is the
                # one `ass_exec` already uses for `bsub`: it keeps the child in
                # this process's group and asks the kernel to signal it if we
                # die, so a command outliving its owner is no more possible
                # locally than on the farm.
                self._results[identity] = _run_locally(produced, bundle)
                return _local_handle(self.name, identity, bundle)
            handle = self._delegate.submit(
                identity, {**bundle, "command": list(produced.argv)}
            )
            return {**handle, "bound": True}

        self._results[identity] = Observation("succeeded", {"value": produced})
        return _local_handle(self.name, identity, bundle)

    def discover(self, identity: str) -> Mapping[str, Any] | None:
        if identity in self._results:
            return {"transport": self.name, "identity": identity, "kind": "local"}
        if self._delegate is not None:
            return self._delegate.discover(identity)
        return None

    def poll(self, handle: Mapping[str, Any]) -> Observation:
        if handle.get("kind") == "local":
            return self._results.get(handle.get("identity")) or Observation("absent")
        if self._delegate is None:  # pragma: no cover - unreachable by construction
            return Observation("absent")
        return self._delegate.poll(handle)

    def cancel(self, handle: Mapping[str, Any]) -> None:
        if handle.get("kind") != "local" and self._delegate is not None:
            self._delegate.cancel(handle)

    def forget(self, identity: str) -> None:
        self._results.pop(identity, None)


def _run_locally(command: Shell, bundle: Mapping[str, Any]) -> Observation:
    """Run a command on this machine and read its exit status as the outcome."""

    from ass_exec.lsf import CommandUnavailable, SubprocessRunner

    try:
        result = SubprocessRunner()(
            list(command.argv), cwd=bundle.get("workdir"), env=bundle.get("env")
        )
    except CommandUnavailable as error:
        raise SubmissionRefused(str(error)) from error
    if result.returncode == 0:
        return Observation("succeeded", {"stdout": result.stdout})
    return Observation(
        "failed",
        {"returncode": result.returncode, "stderr": result.stderr[-2000:]},
    )


def _local_handle(
    name: str, identity: str, bundle: Mapping[str, Any]
) -> dict[str, Any]:
    """A handle for work this transport did itself.

    Carries the workspace, because that is where reconciliation looks for the
    declared files the body was asked to write.
    """

    return {
        "transport": name,
        "identity": identity,
        "kind": "local",
        "workdir": bundle.get("workdir"),
    }


def _wants_workspace(implementation: Callable[..., Any]) -> bool:
    """Whether this body asked for its workspace.

    An operation that writes files declares `out` in its signature. One that
    computes a value does not, and handing it an argument it never named would
    fail the call for no reason.
    """

    import inspect

    try:
        return "out" in inspect.signature(implementation).parameters
    except (TypeError, ValueError):  # pragma: no cover - builtins
        return False
