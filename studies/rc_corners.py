"""One file: author an RC corner sweep, inspect it, run it on real ngspice.

    python studies/rc_corners.py

Small deliberately — an RC low-pass whose -3 dB corner is analytic, so the
result can be checked by hand rather than believed. What it demonstrates is the
whole path in one place: operation bodies that really run, declared outputs
that really land, a placement per invocation, content-addressed reuse on a
second run, and one edited corner rerunning only itself.

    first run   3 corners simulated
    second run  3 corners reused, nothing recomputed
"""

from __future__ import annotations

from pathlib import Path
import math
import shutil
import sys

_HEDLOOM = Path(__file__).resolve().parents[1] / "hedloom"
sys.path.insert(0, str(_HEDLOOM / "src"))
for unit in ("flow", "exec", "run"):
    sys.path.insert(0, str(_HEDLOOM / unit / "src"))

from hedloom import (  # noqa: E402
    Site,
    artifact,
    artifacts,
    file,
    flow,
    local,
    operation,
    parameter,
    returned,
    shell,
    study,
    sweep,
)

DECK = artifact("spice-deck")
RAW = artifact("simulator-raw-results")
CORNER_HZ = artifact("corner-frequency")
VERDICT = artifact("rc-verdict")

CORNERS = ({"key": "cold", "temp_c": -40}, {"key": "nominal", "temp_c": 27},
           {"key": "hot", "temp_c": 125})

RESISTANCE_OHM = 1000.0
CAPACITANCE_F = 1e-9

DECK_TEMPLATE = """* RC low-pass, {key}
.options temp={temp_c}
V1 in 0 AC 1
R1 in out {resistance}
C1 out 0 {capacitance}
.ac dec 50 1k 10meg
.print ac vdb(out)
.end
"""


@operation(config={"key": parameter(str), "temp_c": parameter(int)},
           outputs={"deck": file("corner.cir", kind="spice-deck")})
def write_deck(out, *, key: str, temp_c: int) -> None:
    """A body that writes a declared file. `out.deck` is this attempt's own."""

    out.deck.write_text(
        DECK_TEMPLATE.format(
            key=key,
            temp_c=temp_c,
            resistance=RESISTANCE_OHM,
            capacitance=CAPACITANCE_F,
        )
    )


@operation(inputs={"deck": DECK},
           outputs={"raw": file("corner.raw", kind="simulator-raw-results")})
def simulate(deck, out):
    """A launcher. The command runs at this invocation's placement."""

    # ASCII rather than ngspice's default binary raw: the point of a declared
    # artifact is that another operator can read it without our code.
    return shell(
        "env", "SPICE_ASCIIRAWFILE=1", "ngspice", "-b", "-r", out.raw, deck
    )


@operation(inputs={"raw": RAW},
           outputs={"hz": returned(kind="corner-frequency")})
def corner_frequency(raw) -> float:
    """A value-returning body: nothing is written, the number is the result."""

    magnitudes = _read_ac_magnitudes(Path(raw))
    if not magnitudes:
        raise ValueError(f"{raw} carries no AC sweep to measure")
    reference = magnitudes[0][1]
    for frequency, magnitude in magnitudes:
        if magnitude <= reference / math.sqrt(2.0):
            return frequency
    raise ValueError("the response never fell 3 dB; the sweep is too narrow")


@operation(inputs={"corners": artifacts("corner-frequency")},
           outputs={"verdict": returned(kind="rc-verdict")})
def compare(corners: list) -> dict:
    """The study's conclusion, computed rather than transcribed."""

    expected = 1.0 / (2.0 * math.pi * RESISTANCE_OHM * CAPACITANCE_F)
    return {
        "expected_hz": expected,
        "measured_hz": list(corners),
        "worst_error_pct": max(
            abs(value - expected) / expected * 100.0 for value in corners
        ),
    }


@flow
def rc_sweep(corners):
    """One keyed scope per corner; every call inside gets a stable identity."""

    measured = []
    for corner in sweep(corners, key="key"):
        deck = write_deck(key=corner["key"], temp_c=corner["temp_c"])
        measured.append(corner_frequency(simulate(deck)))
    return {"verdict": compare.named("compare")(measured).verdict}


def _read_ac_magnitudes(path: Path) -> list[tuple[float, float]]:
    """Read frequency and |v(out)| from an ngspice ASCII raw file.

    Written against the format rather than a library, so the example depends on
    nothing but a simulator. A point is an index line carrying the sweep
    variable, then one line per remaining variable, each `real,imaginary`.
    """

    lines = path.read_text(errors="replace").splitlines()
    names: list[str] = []
    reading_variables = False
    start = None
    for index, line in enumerate(lines):
        if line.startswith("Variables:"):
            reading_variables = True
            continue
        if line.startswith("Values:"):
            start = index + 1
            break
        if reading_variables:
            fields = line.split()
            if len(fields) >= 2:
                names.append(fields[1])
    if start is None or "v(out)" not in names:
        return []

    wanted = names.index("v(out)")
    points: list[tuple[float, float]] = []
    frequency = None
    column = 0
    for line in lines[start:]:
        fields = line.split()
        if not fields:
            continue
        if len(fields) == 2 and fields[0].isdigit():
            frequency = float(fields[1].split(",")[0])
            column = 1
            continue
        if frequency is None:
            continue
        if column == wanted:
            real, _, imaginary = fields[0].partition(",")
            points.append((frequency, math.hypot(float(real), float(imaginary))))
        column += 1
    return points


@study(name="rc-corners", default_policy=local())
def rc_corners():
    """The study: every corner swept, in this process."""

    return rc_sweep.named("rc")(CORNERS)


def main() -> int:
    if shutil.which("ngspice") is None:
        print("ngspice is not on PATH; this example needs a real simulator")
        return 1

    here = Path(__file__).resolve().parent
    work = here / "_runs"
    site = Site(
        root=str(work / "attempts"),
        workspace_root=str(work / "work"),
        address_spaces={"repository-relative": str(here)},
    )

    subject = rc_corners()
    print(subject.summary(), "\n")

    run = subject.submit(site=site, watch=True)
    print("\nconclusion:", run.value)
    print("cold corner measured at", run["cold:corner_frequency"].value, "Hz")
    return 0 if run.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
