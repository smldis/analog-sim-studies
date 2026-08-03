# ASS Exec

ASS Exec owns one attempt at one planned invocation, from an identity chosen
before submission through terminal reconciliation. It is the durable half of
execution: the part that must survive the process, worker, and scheduler that
happened to start the work.

The problem it exists for is narrow and specific. Once a batch system accepts a
job, that job outlives whatever submitted it. If the submitting process dies
before learning the job's identity, a naive retry creates a duplicate and a
naive abandon loses it. Neither is acceptable on shared compute, so identity
has to live somewhere durable and be chosen *before* submission.

```python
from ass_exec import (
    AttemptJournal, InProcessTransport, attempt_identity,
    launch_or_attach, reconcile,
)

identity = attempt_identity(plan_id="plan-1", invocation_id="inv-a")
journal = AttemptJournal("attempts", identity.rendered)
transport = InProcessTransport({"double": lambda value: value * 2})

bundle = {"operation": "double", "arguments": {"value": 21}}
result = launch_or_attach(journal, transport, bundle)   # 'claimed'
state = reconcile(journal, transport)                   # 'succeeded'

# Running the same call again attaches or completes; it never reruns.
launch_or_attach(AttemptJournal("attempts", identity.rendered), transport, bundle)
```

Each attempt is a plain directory holding `events.jsonl` and, once terminal,
`manifest.json`. Both are readable without this package.

## Rerunning without repeating work

Declare what an invocation depends on and let the identity be derived from it.
Rerunning then skips work whose inputs are unchanged, and reruns work whose
inputs moved:

```python
from ass_exec.durability import Durability, execute
from ass_exec.reuse import input_digest, stale_attempts

bundle = {
    "operation": "simulate",
    "command": ["ngspice", "-b", "tt.spice"],
    "inputs": {"deck": "sha256:aaa"},          # what the result depends on
    "identity_env": {"PDK_ROOT": "/pdk/sky130A"},
}

execute(lsf, bundle, durability=Durability.RECORDED, root="attempts",
        plan_id="plan-1", invocation_id="inv-tt")
```

Queue, walltime, cores, and general `env` deliberately do **not** participate,
so retuning resources never invalidates a result. Change the deck, and the
invocation lands on a new identity and reruns; the previous result stays on
disk and `stale_attempts(...)` can name it as superseded rather than having
quietly overwritten it.

This trusts your declaration. An operation that reads an undeclared file is not
honestly reusable, and no digest will notice.

Run the evidence with:

```console
python -m pip install -e .
python -m pytest -q
```

`tests/test_failure_injection.py` holds the observations that matter: a
substrate that accepts work and then loses the receipt, a controller that dies
between terminal status and recording it, and a site that cannot be asked
whether it accepted anything. The first two must resolve to exactly one job and
no rerun; the third must fail loudly rather than guess.

## Running on LSF

One selected invocation becomes one `bsub -I` job with its own name, resource
request, and exit status:

```python
from ass_exec.durability import Durability, execute
from ass_exec.lsf import LSFInteractiveTransport

lsf = LSFInteractiveTransport(walltime="30", queue="normal", cores=4)
execute(
    lsf,
    {"command": ["ngspice", "-b", "corner_tt.spice"], "cwd": "run/tt"},
    durability=Durability.RECORDED,
    identity=identity.rendered,
    root="attempts",
)
```

Interactive submission is the mechanism, not a concession to human use: LSF
ties the job to the submitting client, so it cannot outlive the work that
wanted it. The client stays in this process's group and asks the kernel to
signal it if we die, which closes the one gap LSF does not. `-W` is mandatory
as the bound that survives everything else failing.

This holds one process per concurrent job, which is right for a handful of
independently visible jobs and wrong for hundreds. Many similar jobs belong on
a pooled `dask_jobqueue.LSFCluster`; `LSFPooledTransport` marks that boundary
and currently refuses.

The subprocess layer runs for real against a fake `bsub`/`bjobs`/`bkill` on
PATH, and `tests/test_owner_bound.py` proves with real signals that a spawned
child dies when its owner is `SIGKILL`ed. What no local test can establish is
LSF's own guarantee that an interactive job dies with its client. Check that on
a submit host when you have one:

```console
python examples/lsf_preflight.py --queue normal
```

It verifies command availability, interactive admission, `bjobs -J` lookup, and
whether a running job actually disappears once its client is killed. If the
last check fails, the direct mode's premise is wrong.

Worker pools, placement enforcement, retries, and graph scheduling are outside
this unit — see
[`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary and
[`DECISIONS.md`](DECISIONS.md) for what is settled, what is open, and what
would change our minds.
