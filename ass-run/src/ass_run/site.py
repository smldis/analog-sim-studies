"""Everything about a run that is not the study.

A Plan says what to compute. It deliberately does not say which queue exists
here, where records are kept, or what `"repository-relative"` means on this
machine — those are facts about an installation, and putting them in a Plan
would make a study unportable the moment it was authored.

They have to live somewhere, though, and until now they lived as loose
arguments at every call site. A `Site` is that somewhere: placements to
substrates, the roots records and workspaces are written under, and the address
spaces a declared source is resolved through.

Resolving addresses is what unlocks the correctness fix this module exists for.
The invariant:

    A source's identity must change when its content changes.

`ass_exec` identifies a source by its declared address and codec, never by what
is at that address — deliberately, since it resolves no addresses and should
not start. The consequence was that editing an input netlist in place changed
nothing: every downstream invocation was reused, and a study reported results
computed from a file that no longer existed in that form. A run knows what an
address space means, so a run is where the fingerprint belongs.

Sources are **hashed**, not stat'ed. The register's reason for preferring
`mtime` plus size was the cost of hashing multi-GB raw *outputs*; an authored
input is a netlist or a JSON document, and hashing kilobytes costs nothing
while being immune to the mtime churn an ordinary `git checkout` causes.
Anything implausibly large for an authored input falls back to size and mtime,
and says which it used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import blake2b
from pathlib import Path
from typing import Any, Callable, Mapping
import os

from ass_exec.transport import Transport

__all__ = ["Site", "SiteError", "fingerprint_file", "fingerprint_sources"]

_MAX_HASHED_BYTES = 64 * 1024 * 1024
_CHUNK = 1 << 20


class SiteError(RuntimeError):
    """The installation cannot answer something a run needs to know."""


def fingerprint_file(path: Path) -> str:
    """Identify a file by its content, or say plainly that it did not.

    The prefix is part of the value. Two runs that fingerprinted the same file
    by different methods must not look identical, or a study could silently
    reuse across a change the cheaper method could not see.
    """

    stat = path.stat()
    if stat.st_size > _MAX_HASHED_BYTES:
        # Implausible for an authored input. Recorded honestly rather than
        # hashed: this is the weaker signal and the name says so.
        return f"stat:{stat.st_size}:{stat.st_mtime_ns}"
    digest = blake2b(digest_size=16)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return f"blake2b:{digest.hexdigest()}"


@dataclass(frozen=True, slots=True)
class Site:
    """One installation: where work runs, where records go, what addresses mean."""

    root: str
    transports: Mapping[str, Transport] = field(default_factory=dict)
    workspace_root: str | None = None
    address_spaces: Mapping[str, str] = field(default_factory=dict)
    threads: int | None = None
    """Concurrency for the graph kernel. Not a tuning knob this project owns:
    size it from the site's MAX JOB policy and per-user process limits."""

    def with_transports(self, **transports: Transport) -> "Site":
        """Add substrates a configuration file cannot describe.

        An in-process placement needs Python callables, which no TOML holds.
        This seam closes when operations carry their own implementations.
        """

        return Site(
            root=self.root,
            transports={**self.transports, **transports},
            workspace_root=self.workspace_root,
            address_spaces=self.address_spaces,
            threads=self.threads,
        )

    def resolve(self, address: Mapping[str, Any]) -> Path:
        """Turn a declared address into a path on this machine."""

        space = address.get("address_space")
        locator = address.get("locator")
        if space not in self.address_spaces:
            raise SiteError(
                f"this site does not define the address space {space!r} "
                f"(defines: {', '.join(sorted(self.address_spaces)) or 'none'}). "
                "A source cannot be located, so a run cannot tell whether its "
                "inputs changed."
            )
        return Path(self.address_spaces[space]) / str(locator)

    def fingerprints(self, document: Mapping[str, Any]) -> dict[str, str]:
        """Identify every source this Plan declares, by content."""

        return fingerprint_sources(document, self.resolve)

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> "Site":
        """Read a site profile from TOML.

        Relative paths resolve against the profile's own directory, not the
        working directory: a study run from elsewhere must mean the same thing.
        """

        try:
            import tomllib
        except ModuleNotFoundError as error:  # pragma: no cover - Python 3.10
            raise SiteError(
                "reading a site profile needs tomllib (Python 3.11+); "
                "construct Site(...) directly on older runtimes"
            ) from error

        profile = Path(path).resolve()
        with open(profile, "rb") as handle:
            data = tomllib.load(handle)

        base = profile.parent

        def anchored(value: str) -> str:
            return str(base / value) if not os.path.isabs(value) else value

        study = data.get("study") or {}
        if "root" not in study:
            raise SiteError(f"{profile} declares no [study] root")

        return cls(
            root=anchored(study["root"]),
            workspace_root=(
                anchored(study["workspace_root"])
                if study.get("workspace_root")
                else None
            ),
            address_spaces={
                name: anchored(location)
                for name, location in (data.get("address_space") or {}).items()
            },
            transports=_transports_from(data.get("placement") or {}),
            threads=(data.get("kernel") or {}).get("threads"),
        )


def _transports_from(
    placements: Mapping[str, Mapping[str, Any]],
) -> dict[str, Transport]:
    """Build the substrates a profile can describe, and refuse the rest.

    Only kinds whose configuration is entirely data belong here. A placement
    naming an unknown kind is refused rather than skipped: a run that quietly
    lacked a placement would fail later as `UnsupportedPlacement`, blaming the
    Plan for what is a configuration error.
    """

    from ass_exec.lsf import LSFInteractiveTransport

    built: dict[str, Transport] = {}
    for name, options in placements.items():
        settings = dict(options)
        kind = settings.pop("kind", None)
        if kind == "lsf-interactive":
            built[name] = LSFInteractiveTransport(**settings)
        elif kind == "in-process":
            # Needs callables; supplied through with_transports(...).
            continue
        else:
            raise SiteError(
                f"placement {name!r} names an unknown kind {kind!r}; this site "
                "can build 'lsf-interactive' from configuration, and "
                "'in-process' placements must be given their implementations"
            )
    return built


def fingerprint_sources(
    document: Mapping[str, Any],
    resolve: Callable[[Mapping[str, Any]], Path],
) -> dict[str, str]:
    """Fingerprint each declared source, keyed by the Plan's source id.

    A declared source that cannot be found is fatal, and fatal *early*: the
    alternative is a run that reuses results computed from a file nobody can
    show you.
    """

    fingerprints: dict[str, str] = {}
    for source in document.get("sources", []):
        address = source.get("address") or {}
        path = resolve(address)
        if not path.exists():
            raise SiteError(
                f"source {source.get('id')!r} declares {address.get('locator')!r} "
                f"in address space {address.get('address_space')!r}, which "
                f"resolves to {path} and does not exist"
            )
        if path.is_dir():
            # A directory-tree source: identify it by the content of everything
            # under it, so editing one file inside invalidates the study.
            digest = blake2b(digest_size=16)
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    digest.update(str(item.relative_to(path)).encode())
                    digest.update(fingerprint_file(item).encode())
            fingerprints[source["id"]] = f"tree:{digest.hexdigest()}"
        else:
            fingerprints[source["id"]] = fingerprint_file(path)
    return fingerprints
