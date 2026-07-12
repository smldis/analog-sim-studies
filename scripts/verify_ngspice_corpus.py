from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.error import URLError


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from spice_canonical.canonical_netlist import from_file  # noqa: E402


@dataclass(frozen=True)
class CorpusEntry:
    name: str
    url: str
    sha256: str


CORPUS = (
    CorpusEntry(
        name="gain_stage.cir",
        url=(
            "https://raw.githubusercontent.com/ngspice/ngspice/master/"
            "examples/various/gain_stage.cir"
        ),
        sha256="6b46e806f7dc963f45a87ab33e1ce0a667624f362f0e3166fea6425a3bc81d79",
    ),
    CorpusEntry(
        name="inv-meas-tran-control.sp",
        url=(
            "https://raw.githubusercontent.com/ngspice/ngspice/master/"
            "examples/measure/inv-meas-tran-control.sp"
        ),
        sha256="feab0f409f0f99ded643e968583cac9d2ebf66b04dc9ad397e8e5b38a8beae22",
    ),
    CorpusEntry(
        name="ltra1_1_line.sp",
        url=(
            "https://raw.githubusercontent.com/ngspice/ngspice/master/"
            "examples/TransmissionLines/ltra1_1_line.sp"
        ),
        sha256="268ffe38b355dc160e50a64fe2ba04fa94621b683e26d623bd0922d7aab70956",
    ),
)


def _download(entry: CorpusEntry, target: Path) -> None:
    request = urllib.request.Request(
        entry.url, headers={"User-Agent": "sidecar-edits-ngspice-verifier"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
    digest = hashlib.sha256(content).hexdigest()
    if digest != entry.sha256:
        raise RuntimeError(
            f"{entry.name}: upstream content hash changed: {digest}; "
            f"expected {entry.sha256}"
        )
    target.write_bytes(content)


def verify(*, ngspice: str) -> int:
    with tempfile.TemporaryDirectory(prefix="ngspice-corpus-") as directory:
        root = Path(directory)
        for entry in CORPUS:
            netlist_path = root / entry.name
            log_path = root / f"{entry.name}.log"
            _download(entry, netlist_path)

            simulation = subprocess.run(
                [ngspice, "-b", "-o", str(log_path), str(netlist_path)],
                check=False,
                capture_output=True,
                text=True,
                cwd=root,
            )
            if simulation.returncode != 0:
                log = log_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(
                    f"{entry.name}: ngspice returned {simulation.returncode}\n{log}"
                )

            canonical = from_file(netlist_path, spice_format="ngspice")
            if canonical.diagnostics:
                details = "\n".join(
                    f"{item.source}:{item.line}: {item.message}"
                    for item in canonical.diagnostics
                )
                raise RuntimeError(
                    f"{entry.name}: canonical extraction emitted diagnostics\n{details}"
                )
            device_count = len(canonical.top.devices) + sum(
                len(subckt.devices) for subckt in canonical.subcircuits
            )
            print(
                f"PASS {entry.name}: {device_count} devices, "
                f"{len(canonical.subcircuits)} subcircuits"
            )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify official ngspice example netlists with ngspice and the extractor."
    )
    parser.add_argument(
        "--ngspice",
        default=shutil.which("ngspice"),
        help="path to ngspice executable",
    )
    args = parser.parse_args(argv)
    if not args.ngspice:
        parser.error("ngspice executable was not found")
    try:
        return verify(ngspice=args.ngspice)
    except (OSError, RuntimeError, URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
