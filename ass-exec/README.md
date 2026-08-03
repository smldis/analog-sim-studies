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

The only working substrate today is in-process execution. LSF, Dask, worker
pools, placement, retries, and graph scheduling are outside this unit — see
[`ONTOLOGY.md`](ONTOLOGY.md) for the owned boundary and
[`DECISIONS.md`](DECISIONS.md) for what is settled, what is open, and what
would change our minds.
