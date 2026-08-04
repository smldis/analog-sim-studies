"""What a task blocked on external work actually costs a Dask worker.

Three questions, measured rather than argued:

1. Does a worker's thread pool serialise blocked tasks?  (the retracted claim)
2. Does `secede()` release the slot?                      (the correction)
3. Are the blocked waiters cheap?                          (the open question)

A `sleep` subprocess stands in for a `bsub -I` client: our tasks do not
compute, they hold a child process and wait for a farm to finish. Nothing here
touches LSF, so (3) measures the floor — the real per-client cost is the bsub
binary's own resident size, which only a submit host can tell us.

    python prototypes/dask_secede_spike.py
"""

from __future__ import annotations

import os
import subprocess
import threading
import time

WORKERS = 2
THREADS_PER_WORKER = 2
TASKS = 8
HOLD_SECONDS = 3


def hold(seconds: int) -> str:
    """Block on a child process, as a transport waiting on `bsub -I` does."""

    subprocess.run(["/bin/sleep", str(seconds)])
    return "done"


def hold_after_seceding(seconds: int) -> str:
    """The same, having told the worker this thread is no longer computing."""

    from distributed import secede

    secede()
    subprocess.run(["/bin/sleep", str(seconds)])
    # No rejoin: the task ends here. Rejoining only matters if the task wants
    # to compute again afterwards, and would block until a slot is free.
    return "done"


def elapsed(client, function) -> float:
    start = time.monotonic()
    futures = [client.submit(function, HOLD_SECONDS, pure=False) for _ in range(TASKS)]
    client.gather(futures)
    return time.monotonic() - start


def memory_kb(pid: int, field: str = "Pss") -> int:
    """Proportional set size where the kernel offers it, else RSS.

    PSS divides shared pages among the processes mapping them, which is the
    honest measure for many copies of one binary: summing RSS would charge
    every copy for the whole of libc.
    """

    try:
        with open(f"/proc/{pid}/smaps_rollup") as handle:
            for line in handle:
                if line.startswith(f"{field}:"):
                    return int(line.split()[1])
    except OSError:
        pass
    return 0


def measure_client_cost(count: int) -> None:
    """What N simultaneously blocked waiters cost, while they are blocked.

    Each thread holds a child and waits on it, which is the shape of a
    transport waiting on `bsub -I`: one thread and one client process per
    outstanding farm job, doing nothing until the job ends.
    """

    before_threads = threading.active_count()
    before = memory_kb(os.getpid())
    pids: list[int] = []
    lock = threading.Lock()

    def waiter() -> None:
        child = subprocess.Popen(["/bin/sleep", "6"])
        with lock:
            pids.append(child.pid)
        child.wait()  # the thread is genuinely held for the job's lifetime

    threads = [threading.Thread(target=waiter) for _ in range(count)]
    for thread in threads:
        thread.start()

    time.sleep(1.5)  # let them all reach the blocked state
    children = sum(memory_kb(pid) for pid in pids)
    ours = memory_kb(os.getpid()) - before
    held = threading.active_count() - before_threads

    print(f"\n{count} waiters, measured while all are blocked:")
    print(f"  threads actually held : {held}")
    print(f"  client processes PSS  : {children / 1024:.1f} MiB total, "
          f"{children / max(len(pids), 1):.0f} KiB each")
    print(f"  our own PSS growth    : {ours / 1024:.1f} MiB "
          f"({ours / count:.0f} KiB per waiting thread)")
    print("  (/bin/sleep is the floor; bsub links the LSF libraries)")

    for thread in threads:
        thread.join()


def main() -> int:
    from distributed import Client, LocalCluster

    capacity = WORKERS * THREADS_PER_WORKER
    print(
        f"{WORKERS} workers x {THREADS_PER_WORKER} threads = {capacity} slots; "
        f"{TASKS} tasks each holding {HOLD_SECONDS}s"
    )
    print(
        f"serial expectation {HOLD_SECONDS * TASKS / capacity:.0f}s, "
        f"concurrent expectation {HOLD_SECONDS}s\n"
    )

    with LocalCluster(
        n_workers=WORKERS,
        threads_per_worker=THREADS_PER_WORKER,
        processes=True,
        dashboard_address=None,
    ) as cluster, Client(cluster) as client:
        plain = elapsed(client, hold)
        print(f"blocking in the pool   : {plain:5.1f}s")
        seceded = elapsed(client, hold_after_seceding)
        print(f"blocking after secede(): {seceded:5.1f}s")

    measure_client_cost(64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
