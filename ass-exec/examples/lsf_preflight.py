"""Check the assumptions this unit makes about LSF, on a real farm.

Everything here is unreproducible without a cluster, which is exactly why it is
a script you run rather than a test we pretend to pass. Run it once on a submit
host and read the report:

    python examples/lsf_preflight.py --queue normal

The last check is the important one. It verifies the assumption the whole
direct mode rests on: that killing the `bsub` client takes the job with it.
Nothing in the local test suite can establish that.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from ass_exec.lsf import _bind_child_lifetime  # noqa: E402

PASS = "pass"
FAIL = "FAIL"
SKIP = "skip"


def report(status: str, label: str, detail: str = "") -> None:
    print(f"[{status:>4}] {label}" + (f" — {detail}" if detail else ""))


def check_commands() -> bool:
    missing = [name for name in ("bsub", "bjobs", "bkill") if not shutil.which(name)]
    if missing:
        report(FAIL, "LSF commands on PATH", f"missing: {', '.join(missing)}")
        return False
    report(PASS, "LSF commands on PATH")
    return True


def check_interactive(queue: str | None, name: str) -> bool:
    argv = ["bsub", "-I", "-J", name, "-W", "5"]
    if queue:
        argv += ["-q", queue]
    argv += ["/bin/echo", "ass-exec-preflight"]
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        report(FAIL, "interactive submission", "timed out after 300s")
        return False
    if completed.returncode != 0 or "ass-exec-preflight" not in completed.stdout:
        report(
            FAIL,
            "interactive submission",
            f"rc={completed.returncode} {completed.stderr.strip()[:200]}",
        )
        return False
    report(PASS, "interactive submission", "-I accepted and output captured")
    return True


def check_name_lookup(name: str) -> bool:
    completed = subprocess.run(
        ["bjobs", "-J", name, "-noheader"], capture_output=True, text=True
    )
    # A finished job may legitimately be absent; what matters is that the
    # command is accepted rather than rejecting -J outright.
    if "Illegal option" in completed.stderr or "Unknown option" in completed.stderr:
        report(FAIL, "lookup by job name", completed.stderr.strip()[:200])
        return False
    report(PASS, "lookup by job name", "bjobs -J accepted")
    return True


def check_owner_bound(queue: str | None, name: str) -> bool:
    """The assumption the direct mode rests on: job dies with its client."""

    argv = ["bsub", "-I", "-J", name, "-W", "10"]
    if queue:
        argv += ["-q", queue]
    argv += ["/bin/sleep", "300"]

    client = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=_bind_child_lifetime(),
    )

    # Give LSF time to actually start the job before killing the client.
    deadline = time.monotonic() + 120
    started = False
    while time.monotonic() < deadline:
        found = subprocess.run(
            ["bjobs", "-J", name, "-noheader"], capture_output=True, text=True
        )
        if found.returncode == 0 and " RUN " in f" {found.stdout} ":
            started = True
            break
        time.sleep(2)

    if not started:
        client.kill()
        report(SKIP, "job dies with its client", "job never reached RUN; try again")
        return False

    client.kill()
    client.wait(timeout=30)

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        found = subprocess.run(
            ["bjobs", "-J", name, "-noheader"], capture_output=True, text=True
        )
        if found.returncode != 0 or not found.stdout.strip():
            report(PASS, "job dies with its client", "job gone after client kill")
            return True
        if " RUN " not in f" {found.stdout} ":
            report(PASS, "job dies with its client", "job left RUN after client kill")
            return True
        time.sleep(3)

    subprocess.run(["bkill", "-J", name], capture_output=True)
    report(
        FAIL,
        "job dies with its client",
        "job still RUNNING 90s after the client was killed — owner-bound "
        "lifetime is NOT enforced here; the design needs revisiting",
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", default=None, help="queue to submit to")
    parser.add_argument(
        "--skip-lifetime",
        action="store_true",
        help="skip the slow owner-bound check",
    )
    args = parser.parse_args()

    token = uuid.uuid4().hex[:8]
    print(f"ass-exec LSF preflight (run token {token})\n")

    if not check_commands():
        return 1

    ok = check_interactive(args.queue, f"ass-preflight-{token}-a")
    ok = check_name_lookup(f"ass-preflight-{token}-a") and ok
    if not args.skip_lifetime:
        ok = check_owner_bound(args.queue, f"ass-preflight-{token}-b") and ok
    else:
        report(SKIP, "job dies with its client", "skipped by request")

    print()
    print("All assumptions hold." if ok else "At least one assumption failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
