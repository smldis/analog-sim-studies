# Analog Sim Studies

This is the project-wide composition guide. The manifesto defines the intended
system; the root ontology and architecture note describe the implemented
boundaries. Child documentation below is composed programmatically from the
sources owned by each immediate unit.

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
reference/ota-pvt-plan/README
_composed-children
```

The generated child page is created by `python composition.py docs`; it is not
maintained source.

The OTA/PVT reference is root-owned composition evidence only. It declares an
inspectable static Plan across child and unimplemented domain boundaries; it
does not execute those boundaries or introduce adapters, runtime state, or a
new component.
