"""Watch a sweep that another process is running.

    python examples/watch_sweep.py attempts --interval 10

Point it at the attempt root a run is writing to. It asks LSF once per refresh
about every live job, records transitions beside each attempt, and prints one
line per invocation.

It is a *client* of the record, not part of the run: start it late, stop it,
restart it, or run two of them, and no result changes. What it writes is
evidence about attempts, never a transition of them.

The queued column is the per-job dispatch cost, measured. It is the number that
decides whether pooled placement would ever be worth its complexity — a corner
that waits two seconds and simulates for ten minutes says one thing, and a step
that waits forty seconds to do two seconds of work says the opposite.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from hedloom_exec.transport import TransportError  # noqa: E402
from hedloom_exec.watch import live_attempts, observe, render  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="the attempt root a run is writing to")
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="seconds between refreshes (one bjobs call each, not one per job)",
    )
    parser.add_argument(
        "--once", action="store_true", help="print one refresh and exit"
    )
    args = parser.parse_args()

    while True:
        try:
            rows = observe(args.root)
        except TransportError as error:
            # Being unable to ask is not a claim about any job. Say so and keep
            # watching: the farm may answer on the next refresh.
            print(f"[warn] {error}")
            rows = live_attempts(args.root)

        print(f"\n{time.strftime('%H:%M:%S')}  {len(rows)} in flight")
        print(render(rows))

        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
