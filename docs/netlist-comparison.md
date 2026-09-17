# Compare netlist revisions

SPICE Canonical extracts the available structure; Netlist Comparison proposes
counterparts and differences to inspect on two schematics. Their pinned ASS
revisions share the canonical artifact contract. The original simulator inputs
remain authoritative, and a proposed pairing is not an identity or equivalence
proof. Start with `netlist-compare --guide` for the maintained feature guide;
`netlist-compare --help` and `netlist-compare view --help` list available options.

## Extract once, including external cells

```bash
spice-canonical before.sp --external-subcircuits pins.json --output before.canonical
spice-canonical after.sp --external-subcircuits pins.json --output after.canonical
netlist-compare before.canonical --format canonical --inspect
```

The optional `pins.json` maps external cell names to formal pins in call order,
for example `{"nmos_lvt": ["d", "g", "s", "b"], "res_cell": ["p", "n"]}`.
Omit `--external-subcircuits` when only positions are known; tokens `@1`, `@2`,
and so on retain that distinction. Missing library bodies remain unavailable,
while available connections, overrides, defaults and diagnostics survive in
SPICE Canonical's custom tables. The netlist artifact is not JSON.

## Compare and retain the evidence

```bash
netlist-compare before.canonical after.canonical --format canonical \
  --black-box-missing --matching-mode regional \
  --omission-work-limit 512 --swap-work-limit 512 --output result.json
```

`--black-box-missing` assumes stable cell references/interfaces and unchanged
hidden implementations. It lets visible boundary connections and raw overrides
participate without library bodies. Incompatible interfaces and definitions
available on only one side remain unresolved. Pin labels do not supply hidden
functionality or eliminate matching limitations.

Regional matching is experimental and opt-in; `fixed` remains the default.
Omission search reopens occupied partners for currently omitted objects. Paired
swaps challenge assignments even when every object already has a partner. Both
budgets default to zero and count full-map score evaluations, not elapsed time
or RAM. Extra budget cannot supply a missing regional frontier. `anchor_growth`
is another diagnostic mode when regional returns no pairs, with its own tentative
anchor assumptions and failure modes.

For repeated certified components, `--component-presentation minimum_raw` can
reduce avoidable parameter noise without changing represented incidence or
removing structural ambiguity. It is a representative choice, not proof of which
physical copy changed. Explicit global nets belong in repeatable `--global-net`
options; do not assert `--globals-complete` without knowing the full set.

To compare two calls within one full netlist, use the actual paths from inspection:

```bash
netlist-compare full.canonical --format canonical --black-box-missing \
  --path-a TOP/X1 --path-b TOP/X2 --output instances.json
```

This retains selected pin bindings and original hierarchy locations. Selecting
unavailable cell internals is rejected. A canonical file root and subcircuit with
the same name currently require a deliberate file-root rename before comparison.

## Focus a saved result

```bash
netlist-compare view result.json --omit-parameters --group-depth 2 --text
netlist-compare view result.json --under-a TOP/XOLD --under-b TOP/XNEW \
  --category wiring --text
netlist-compare view result.json --parameter W --category raw --output widths.view.json
```

Saved views do not rerun matching. Selecting either side retains its opposite
counterpart, including moves across hierarchy. Parameter suppression hides sizing
detail while keeping structural references, wiring and unresolved scope; defaults
and call overrides remain unfiltered context. Group depth is relative to selected
roots and reports conditional hierarchy membership, not inferred split/merge events.

Text is a bounded preview; `--limit` changes displayed rows only. Saved JSON retains
the complete evidence and coupled alternatives. Whole-comparison population and
search context stays explicitly labelled even in subtree views. Joint population
surplus differs from knowing which occurrence is new: repeated objects can each
have a possible counterpart while one occurrence must remain outside every map.

## Evidence and remaining gaps

Small public-topology mutation trials improved a 285-pair redesign from three
terminal discrepancies to one. Later paired swaps reduced two renamed cases to
six discrepancies, but a verified feasible alignment with two is still missed.
These are structural development controls, not electrically validated redesigns.
An unchanged connected 129-leaf control still produces no regional frontier and
zero pairs. Repeated synthetic scale results do not establish general accuracy
for thousands of leaves at four or five hierarchy levels.

Use the output to choose schematic locations to inspect. Counts of pairs, wiring
rows or tests are not independent design edits or a confidence measure. Real
workplace validation, better connected admission and better proposals across the
remaining search barrier are still needed. Algorithm contracts and detailed limits
remain in the [comparison guide](../netlist-comparison/docs/index.md); artifact
semantics belong to [SPICE Canonical](../spice-canonical/docs/representation.md).
