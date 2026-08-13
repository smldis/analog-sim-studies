# Hedloom Exec

Hedloom Exec owns one attempt at one planned invocation, from an identity chosen
before submission through terminal reconciliation. It is the durable half of
execution: the part that must survive the process, worker, and scheduler that
happened to start the work.

The problem it exists for is narrow and specific. Once a batch system accepts a
job, that job outlives whatever submitted it. If the submitting process dies
before learning the job's identity, a naive retry creates a duplicate and a
naive abandon loses it. Neither is acceptable on shared compute, so identity
has to live somewhere durable and be chosen *before* submission.

```python
from hedloom_exec import (
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
from hedloom_exec.durability import Durability, execute
from hedloom_exec.reuse import input_digest, stale_attempts

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

## The end-to-end slice

`plan_bundles(...)` turns an Hedloom Flow Plan document into content-addressed
bundles, so a rerun skips what is unchanged. Run it:

```console
PYTHONPATH=src:../flow/src python examples/planned_characterization.py
```

```
First run — nothing is published yet
  ran     corner-tt    23f06873c974
  ran     corner-ss    29a9d0839b44
  ran     corner-ff    9c5522647f21
  ran     summary      9ce639729b3e

Third run — ss retuned to 150C
  reused  corner-tt    23f06873c974
  ran     corner-ss    ee96c3bf59dc
  reused  corner-ff    9c5522647f21
  ran     summary      65a90b965369
```

The coupling is to the Plan *document*, not the package: nothing imports
`hedloom_flow`, so the base distribution stays dependency-free and any producer of
the same schema-2 document works. An invocation's digest changes exactly when
its own declaration or any ancestor's does, which is what makes the edited
corner and its reduction rerun while the untouched corners are reused.

## Outputs that are files

Most real commands write their answer to disk and print progress. Declare which
files matter; the rest stays as unnamed evidence:

```python
execute(
    lsf,
    {
        "command": ["ngspice", "-b", "corner_tt.spice"],
        "outputs": {"raw": {"path": "corner_tt.raw"}},
    },
    durability=Durability.RECORDED,
    root="attempts",
    workspace_root="/nfs/studies/ota-pvt",
    plan_id="ota-pvt",
    invocation_id="corner-tt",
)
```

The attempt runs in its own directory under `workspace_root`, and the manifest
records each declared output's address, size, and modification time. On a shared
filesystem that is the whole of materialization — the next invocation opens the
same path, and nothing is copied. `result.address("raw")` gives it back.

Standard output always lands in `stdout.log` as diagnostics. It becomes a result
only if an operation declares `{"stream": "stdout"}`. A declared output that
never appears fails the invocation rather than publishing a manifest that points
at nothing.

## Running on LSF

One selected invocation becomes one `bsub -I` job with its own name, resource
request, and exit status:

```python
from hedloom_exec.durability import Durability, execute
from hedloom_exec.lsf import LSFInteractiveTransport

lsf = LSFInteractiveTransport(walltime="30", queue="normal", cores=4)
execute(
    lsf,
    {"command": ["ngspice", "-b", "corner_tt.spice"], "cwd": "run/tt"},
    durability=Durability.RECORDED,
    root="attempts",
    plan_id="ota-pvt",
    invocation_id="corner-tt",
)
```

The constructor sets site defaults. What an individual job asks for comes from
the placement the Plan resolved for it, which the driver puts on the bundle:

```python
{
    "command": ["ngspice", "-b", "corner_ss.spice"],
    "placement": {
        "requested": {
            "name": "lsf-direct",
            "options": {
                "queue": "bigmem",
                "cores": 16,
                "memory_mb": 32000,
                "licences": {"spectre": 1},
            },
        }
    },
}
```

That job, and no other, is submitted with
`-q bigmem -n 16 -R rusage[mem=32000,spectre=1]`. A licence is *declared*, never
counted here: LSF knows how many exist and who holds them, so the request goes
to the scheduler that can arbitrate it — use the resource name your site
configured, and check it with `lsf_preflight.py --licence <name>`. An option
this transport cannot express as a `bsub` argument refuses before submission
rather than being dropped, because running the work without a resource it asked
for is not the same experiment. None of it reaches the input digest: retuning a
corner's memory reuses the result it already produced.

Interactive submission is the mechanism, not a concession to human use: LSF
ties the job to the submitting client, so it cannot outlive the work that
wanted it. The client stays in this process's group and asks the kernel to
signal it if we die, which closes the one gap LSF does not. `-W` is mandatory
as the bound that survives everything else failing.

One job per invocation costs one queue dispatch, which is negligible for work
that runs for minutes and ruinous for work that runs for seconds. It buys a
per-corner resource request, `bkill`, logs, accounting, licence arbitration by
LSF, and failure isolation. Short repetitive steps are what belong on a pooled
`dask_jobqueue.LSFCluster` instead; `LSFPooledTransport` marks that boundary and
currently refuses.

Concurrency is a separate matter: each simultaneously running job holds a
blocked client on the submit host, so the practical limit is your site's
per-user process and pending-job policy.

The subprocess layer runs for real against a fake `bsub`/`bjobs`/`bkill` on
PATH, and `tests/test_owner_bound.py` proves with real signals that a spawned
child dies when its owner is `SIGKILL`ed. What no local test can establish is
LSF's own guarantee that an interactive job dies with its client. Check that on
a submit host when you have one:

```console
python examples/lsf_preflight.py --queue normal
```

It verifies command availability, interactive admission, `bjobs -J` lookup, that
a composed resource requirement is admitted (add `--licence <name>` to include
one of your site's licence resources), and whether a running job actually
disappears once its client is killed. If the last check fails, the direct
mode's premise is wrong.

Worker pools, placement enforcement, retries, and graph scheduling are outside
this unit — see
[`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary and
[`DECISIONS.md`](DECISIONS.md) for what is settled, what is open, and what
would change our minds.
