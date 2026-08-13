# Hedloom internals

For working *on* this package rather than with it. Nothing here is needed to
author or run a study — that is [the Hedloom page](index.md).

## Why this unit exists at all

`hedloom_flow` owns authoring and the Plan. `hedloom_exec` owns one attempt's durable
record and imports neither this package nor Dask. `hedloom_run` owns binding and
readiness. This package composes them and adds the one thing none of them
could own alone: a `submit` that runs what was authored, because it holds both
halves.

Before it, an `@operation` body was dead code — `hedloom_flow` kept the function
but nothing ever called it — and a study needed a second file supplying real
implementations, command lines and output paths. For the OTA/PVT reference
that file was six hundred lines whose only job was to agree with the first
one. Every seam between the two was a place where the study could mean
something other than what was authored. See `hedloom/ONTOLOGY.md` for the fuller
argument and its evidence.

## What this unit does not do

`hedloom` owns no attempt record, no identity, no reuse policy, no transport, no
readiness, and no Plan validation. It composes those four responsibilities
into one operator gesture; each of them remains exactly where it was, and
`hedloom_exec` in particular still imports neither `hedloom_flow` nor Dask, which is
what keeps the durable record and this façade independently replaceable.

The practical consequence for a contributor: a bug in reuse belongs in
`hedloom_exec`, a bug in readiness or placement belongs in `hedloom_run`, and a bug in
what the Plan says belongs in `hedloom_flow`. What belongs here is only the
composition — binding authored bodies to planned invocations, and the one
`submit` that joins the halves.

## Staged plans

An invocation may itself author and submit an inner Plan — see
`hedloom/examples/ota_pvt_clean_nested.py`. Nothing here is result-dependent
control: no plan branches on its own result. Plans are *staged* instead — each
one is fully determined at the moment it is authored, and a later stage is
authored only after the earlier stage has already produced the ordinary Python
values it needs. The invariant ("a Plan predicts what will run before anything
runs") holds per plan, exactly where it was always stated; it is just that "a
study" may now be more than one plan, submitted in sequence by ordinary Python
code inside one invocation.

This is recorded as "already demonstrated: staged plans" in
`docs/vision/open-concepts.md` at the repository root, along with the open
questions it leaves: a coarse source fingerprint that invalidates every corner
when only the corner list changed, and an inner run's records root arriving as
authored config, which bakes a machine path into the outer plan's identity.

## Further reading for contributors

- [`hedloom/ONTOLOGY.md`](https://github.com/smldis/analog-sim-studies/blob/main/hedloom/ONTOLOGY.md)
  — this unit's current contracts, and what its examples have and have not
  demonstrated. In particular: every placement run against a real substrate so
  far is `local`; the `lsf` launcher path is designed and untested against a
  real farm.
- `hedloom-flow/docs/architecture.md` — the authoring model and the Plan IR,
  including the experimental Dask lowering `hedloom.visualize` draws from.
- `hedloom-exec/docs/index.md` — attempt identity, the journal, and the reuse
  decision this package defers to.
- `hedloom-run/docs/index.md` — the two kernels, binding rules, and `Site`.
