# Sidecar Edits Ontology

## Purpose and scope

Sidecar Edits turns an authored base simulation directory and typed Python edit
declarations into one or more concrete run directories. It owns edit-file
loading, parameter sets and matrices, traced file/text operations, PWL table
generation, and the native subcircuit extraction helper used by those edits.

## Mode of being

**Development state:** `prototype`

Its present runnable form studies which typed, inspectable edit operations and
parameter conventions can replace repeated manual simulation-directory setup
without taking authority from the authored base. Real examples, skipped or
failed edits, and awkward preparation flows are evidence for revising the API,
the materialization boundary, or this account of the unit. The capability is
useful now, but its current operation set and packaging are not presumed final;
extensions should remain explicit, reversible, and tested in proportion to
their risk.

## Current contracts

- Python imports: `sidecar_edits`, `sidecar_edits.edits`, and
  `sidecar_edits.pwl`.
- CLI: `sidecar-render`.
- Authored inputs: a Python edit file, its base directory, optional parameter
  JSON/workbooks, and referenced assets.
- Materialized output: copied and edited run directories; the base remains
  authoritative.
- Build contract: the C helper source is package data and is compiled by the
  package build or lazily through the installed package.

## Contribution to the parent

The unit contributes a reviewable, headless preparation operation for simulation
inputs. Its examples demonstrate the current end-to-end slice.

## Exclusions

It does not parse a canonical circuit graph, decompose circuit function, launch
simulators, evaluate results, schedule studies, or own project-wide policy.

## Child composition

There are currently no child units.
