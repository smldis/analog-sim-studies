# Study Flow

Study Flow is a conceptual, runnable prototype of Dask as a replaceable ASS
execution substrate. It is intentionally smaller than a study runtime and does
not make Dask the owner of authored intent, artifacts, evidence, or decisions.

The reference workflow contains one dependency run synchronously by the
controller and two identical basic flows that Dask maps and reduces:

```text
prepare locally -> prepared.json
        |
        +-> simulate(low)  -> measure(low)  -+
        |                                     +-> reduce -> summary.json
        +-> simulate(high) -> measure(high) -+
```

`simulate` and `measure` are arithmetic placeholders. Their purpose is to make
task boundaries, worker execution, filesystem publication, and reduction
visible without requiring a simulator or compute farm.

## Install and run locally

From this directory:

```bash
python -m pip install -e .
ass-flow-demo --output build/demo
```

The command starts two local threaded Dask workers. It prints the locations of
the derived plan and reduced summary. Every run gets a new directory, so an
existing result is never silently replaced.

## Run through Dask Jobqueue on LSF

The same graph can allocate Dask workers through LSF:

```bash
ass-flow-demo \
  --backend lsf \
  --queue normal \
  --project my-project \
  --interface eth0 \
  --output /shared/path/ass-flow-runs
```

The output path and installed Python environment must be visible from the
submission host and every worker. Use repeated `--job-prologue` arguments when
the site requires module or environment setup, and `--python-executable` when
workers must use a different shared installation. The LSF worker script is
saved beside the plan before worker jobs are scaled.

Each cluster uses random scheduler ports and per-cluster mutual TLS. The Dask
dashboard binds to loopback. These defaults prevent accidental port clashes and
reject clients or workers that do not hold the cluster credentials; they do not
replace site policy or a managed multi-user service.

## What the files mean

```text
<run-id>/
├── study-spec.json
├── prepared.json
├── plan.json
├── lsf-worker-job.sh       # LSF backend only
├── .dask-control/          # private temporary TLS material during LSF runs
├── attempts/
│   ├── low/<attempt-id>/
│   │   ├── simulation.json
│   │   └── measurement.json
│   └── high/<attempt-id>/
│       ├── simulation.json
│       └── measurement.json
└── summary.json
```

The spec snapshot, plan, and produced files remain after the Dask cluster
closes. Futures are temporary handles; they are not the historical record. The
current files are demonstration artifacts rather than a stable schema or
complete provenance model.
The LSF helper creates `.dask-control` with owner-only permissions because its
temporary credentials must be visible to workers through shared storage.
Dask Jobqueue retains those files for the lifetime of the cluster object; an
abnormally terminated controller may therefore leave private control material
for the operator to inspect and remove.

## Deliberately deferred seams

`ass-flow-demo --list-deferred` prints the questions left open by the
prototype. They include real simulator adapters, restart reconciliation,
artifact identity and staleness, evidence promotion, executor routing, policy,
adaptive planning, and CACE-shaped domain profiles. These entries are research
stubs, not claims that the architecture is already settled.
