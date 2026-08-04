# ASS

Author a study, see what it will do, and run it — from one file.

```python
from ass import Site, artifact, file, flow, local, operation, plan, shell, study, sweep

DECK = artifact("spice-deck")

@operation(config={"temp_c": parameter(int)}, outputs={"deck": file("corner.cir")})
def write_deck(out, *, temp_c):
    out.deck.write_text(render(temp_c))          # the body really runs

@operation(inputs={"deck": DECK},
           outputs={"raw": file("corner.raw")},
           policy=lsf(queue="normal", cores=4, licences={"ngspice": 1}))
def simulate(deck, out):
    return shell("ngspice", "-b", "-r", out.raw, deck)   # runs at its placement

@flow
def sweep_corners(points):
    for point in sweep(points, key="key"):        # keyed scope per corner
        yield simulate(write_deck(temp_c=point["temp_c"]))

subject = study(build_plan())
print(subject.summary())                          # nothing spent yet
run = subject.submit(site=Site.from_file("site.toml"), watch=True)
print(run["cold:simulate"].artifacts["raw"]["address"])
```

`examples/rc_corners.py` is the whole of that, runnable, against real ngspice:
three RC corners whose -3 dB frequency is analytic, so the answer can be
checked rather than believed.

## What this unit adds

Nothing that the three units below it could not already do — it removes the
seam between them. Before it, an operation body was dead code, and a study
needed a second file supplying implementations, command lines, output paths,
transports and roots; for the OTA reference that file is six hundred lines
whose only job is to agree with the first one.

- **The body is the implementation.** `@operation` here is `ass_flow`'s,
  wrapped so the function it already kept is remembered as callable. The Plan
  records `module:qualname` and a fingerprint of the source, so an edited body
  reruns the work it produced instead of relying on someone bumping `version`.
- **`out` is the attempt's own workspace.** A body writing `out.deck` writes
  where the executor will look, because both read one declaration.
- **`shell(...)` is a launcher.** Returning a command instead of running one is
  what lets it reach a placement: locally it is a subprocess, on `lsf` it is one
  `bsub -I` job with that corner's queue, cores and licence.
- **`sweep(points, key=...)`** keys every call inside the loop, so reuse cannot
  be lost to renumbering — the trap that made unkeyed invocations dangerous.
- **`Site`** holds what is not the study: placements, roots, address spaces,
  threads. From TOML, with relative paths anchored to the profile.

## What it does not change

`ass-exec` still owns one attempt's durable record and imports neither this
package nor Dask. `ass-run` still owns binding and readiness, so `submit` on a
Dask client is the same run on a different kernel. Reuse, identity, placement,
licences, the watcher — untouched. This unit composes; it does not reimplement.

```console
PYTHONPATH=src:../ass-flow/src:../ass-exec/src:../ass-run/src python -m pytest -q
python examples/rc_corners.py
```
