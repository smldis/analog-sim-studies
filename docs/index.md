# Analog Sim Studies

This is the project-wide composition guide. The manifesto defines the intended
system; the root ontology and architecture note describe the implemented
boundaries. Child documentation below is composed programmatically from the
sources owned by each immediate unit — see "Composed child documentation" in
the sidebar for every unit's own page.

Four units compose one author-plan-execute-evaluate path: `ass-flow` authors
a Plan, `ass-exec` owns one attempt's durable record, `ass-run` walks the
Plan and executes it, and `ass` composes all three into the front door most
readers want — start there. Three further units (`sidecar-edits`,
`spice-canonical`, `netlist-decomposition`) contribute netlist preparation,
canonicalization, and structural recognition, composed together with the
first four in the root-owned OTA/PVT reference below.

```{toctree}
:maxdepth: 3
:caption: Composition

architecture
manifesto
vision/conceptual-flow-foundation
vision/ass-flow-rebuild-main
vision/deferred-study-runtime-research
vision/manifesto-challenges
vision/manifesto-change-catalog
vision/open-concepts
vision/documentation-open-points
reference/ota-pvt-plan/README
_composed-children
```

The generated child page is created by `python composition.py docs`; it is not
maintained source.

The OTA/PVT reference is root-owned composition evidence only. It declares an
inspectable static Plan across child and unimplemented domain boundaries; it
does not execute those boundaries or introduce adapters, runtime state, or a
new component.
