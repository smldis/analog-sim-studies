# Documentation open points

Written during the docs pass that fixed `hedloom`, `hedloom-flow`, `hedloom-exec`,
`hedloom-run`, and root-level integration (task: bring the four execution units'
docs up to date and route the root index to all of them). Every place I could
not resolve something myself, had to pick between disagreeing sources, or
found a fix that needs a code change rather than a docs change, is recorded
here — one section each, self-contained.

## 1. My worktree branched from a stale point; local `main` was ahead

**What I found.** My worktree (`worktree-agent-ad43cfa7f8bef1571`) was created
from `origin/main` (`70706f8`), but the primary checkout's local `main` branch
was four commits ahead and unpushed, ending at `da2a606 feat: run the OTA
sign-off study on Dask, with the dashboard open first`. Those four commits are
exactly the ones the task brief's "Established findings" describe: the Dask
`LocalCluster`/dashboard/`--fresh`/`SIMULATOR_HOLD_SECONDS` behaviour in
`hedloom/examples/ota_pvt_clean.py`, and the `hedloom.visualize` module (added in
`0c6d226 feat: recover the Delayed lowering, for looking at a study`). Neither
existed anywhere in the repository at my worktree's original base commit —
`grep -r visualize` and `grep -r LocalCluster` both returned nothing.

**What I did.** I rebased my worktree branch onto local `main` (`git rebase
main`, after removing an untracked `.toolchain` symlink that blocked the
checkout) before writing anything, so the documentation describes the code
that is actually there. All the facts in the new `hedloom/docs/index.md` about
Dask, `--fresh`, `SIMULATOR_HOLD_SECONDS`, and `hedloom.visualize` were re-verified
by reading the rebased source, not assumed from the task brief.

**What I did not do.** I did not look at the further branch
`worktree-cluster-exposure` (one more commit, `8262d9c feat: let a site say
what its cluster exposes`, beyond local `main`). It is a separate, apparently
live worktree; merging or reading its content felt out of scope for a docs-only
task against `main`, and it may still be in progress. If it lands on `main`
before this PR merges, `hedloom/docs/index.md`'s `Site` section may need a
follow-up for whatever "a site says what its cluster exposes" turns out to
mean.

**Recommendation.** If local `main` and `origin/main` are meant to converge
(push the four unpushed commits), do that before merging this PR, since this
PR's base is local `main`'s tip and a push-then-merge order avoids rebasing
this branch again.

## 2. `docs/vision/hedloom-flow-rebuild-main.md` → `hedloom-flow/docs/architecture.md`: link fixed for the build, not for GitHub

**File/line.** `docs/vision/hedloom-flow-rebuild-main.md`, the "architecture and
research ledger" link (was line 254).

**What I found.** This link, `../../hedloom-flow/docs/architecture.md`, resolves
correctly when the file is read directly on GitHub (repo-root-relative), but
broke in the Sphinx build because `composition.py`'s `stage_docs` copies each
child's docs tree under `children/<unit-id>/...`, not at the child's real
repository path.

**What I assumed / did.** Per the task's instruction not to redesign
`composition.py`, I fixed it from the docs side: changed the link to
`../children/hedloom-flow/docs/architecture.md`, which is correct in the staged
Sphinx source tree. This is a real tradeoff, not a clean win: **the link no
longer resolves when this file is read directly on GitHub** (there is no
`docs/children/` directory in the actual repository), where the *original*
link did work. I chose the build-correct version because this file's evident
purpose is deep prose that is primarily meant to be read as part of the built
docs site, and the file was already 8/8 broken-in-the-build before my change.

**What I would do with more scope.** The clean fix is a `composition.py`
feature: let a root-owned doc declare "this cross-unit link should resolve to
`children/<id>/...` in the composed tree, and to the real relative path
outside it" — effectively two link forms for one relationship, or a build-time
rewrite pass. That's a `composition.py` change, out of scope here.

## 3. The same tradeoff, smaller scale: `docs.resources` directories change a link's real target

**File/line.** `hedloom/unit.toml`, `hedloom-flow/unit.toml` (new `resources =
["examples"]` entries); `hedloom-exec/unit.toml` (`resources = ["DECISIONS.md"]`).

**What I found.** `composition.py`'s `stage_docs` copies a declared resource
to `child_stage / resource.name` — i.e., it drops any subdirectory prefix from
a *file* resource, but preserves the whole subtree for a *directory* resource
(`shutil.copytree`). This means declaring `resources = ["examples/foo.py"]`
places the file at `children/<id>/foo.py`, **not** `children/<id>/examples/foo.py`
— which would silently break a `../examples/foo.py` link even after being
"fixed", the opposite of what a docs author would expect from the declaration
name.

**What I did.** For `hedloom-flow` and `hedloom` I declared the *directory*
(`resources = ["examples"]`) rather than individual files, which preserves the
`examples/` prefix in the staged tree and keeps `../examples/whatever.py`
links working exactly as authored. For `hedloom-exec` I declared the single file
`DECISIONS.md` (no subdirectory, so the flattening is a no-op) — this also
transitively fixed the identical broken link inside
`hedloom-flow/docs/architecture.md` (`../../hedloom-exec/DECISIONS.md`), since both
links resolve to the same staged file once the resource exists.

**What I would flag for review.** `resources = ["examples"]` now stages
*every* file in `hedloom-flow/examples/` and `hedloom/examples/` into the built docs
site (visible under "downloadable files" in the Sphinx build log), not just
the ones actually linked from `docs/index.md`. For `hedloom-flow` that's two files
(`characterization.py`, `local_dask_characterization.py`) — no surprise. For
`hedloom` that's `ota_pvt.py`, `ota_pvt_clean.py`, `ota_pvt_clean_nested.py`, and
`rc_corners.py` — all four ship into the docs build now, which I think is
fine (they're already public, runnable examples, and the docs page names three
of the four explicitly), but flagging it as a scope decision rather than
something obviously correct.

## 4. `hedloom-exec/docs/index.md` now carries a hidden toctree pulling in `DECISIONS.md`

**File/line.** `hedloom-exec/docs/index.md`, trailing `{toctree}` block.

**What I found.** Once `DECISIONS.md` became a `docs.resources` entry (point
3 above), Sphinx started treating it as a document that must appear in some
toctree, or warn `toc.not_included`. It was already linked in prose
(`[DECISIONS.md](../DECISIONS.md)`), but a prose link doesn't satisfy Sphinx's
toctree-membership check.

**What I did.** Added a `:hidden:` toctree entry so it's structurally
included (satisfies the check, doesn't visually duplicate the existing prose
link in the rendered page). This is a small mechanical fix, not a content
judgment call — flagging it only so the pattern is understood if the same
warning appears again when another unit gains a `docs.resources` file.

## 5. `hedloom-flow/docs/architecture.md` (30 KB) — checked for staleness on the two topics I could verify quickly, not read end to end

**What I found.** The instruction was "check it for staleness rather than
rewriting it." I verified two things I could check mechanically:
- It nowhere documents `HandleUsedAsValue` (`__bool__`/`__eq__` refusing) —
  I added that to `hedloom-flow/docs/index.md` instead, since `architecture.md`
  reads as a historical research ledger (dated entries, a "review vocabulary"
  of adopt/discard/adapt) rather than a living API reference, and adding a
  present-tense API fact into it seemed like the wrong home.
- It frames Dask as "the first execution hypothesis to test" for *this
  unit's own* bounded `local_dask` experiment, which is still accurate — that
  experiment is unrelated to `hedloom-run.graph`'s now-adopted Dask kernel, a
  different unit's decision the ledger predates and doesn't claim to cover.

**What I did not do.** I did not read the remaining ~28 KB (mostly the LSF/
Dask research sections, `## Preserved execution research` onward) closely
enough to certify no other claim has gone stale relative to `hedloom-exec`'s and
`hedloom-run`'s current LSF/Dask state. A slower pass cross-checking every dated
claim against current `hedloom-exec`/`hedloom-run` contracts would be worth doing
separately.

## 6. `hedloom/ONTOLOGY.md` does not mention `hedloom.visualize` or the Dask cluster example

**What I found.** `hedloom/ONTOLOGY.md`'s "Current contracts" and "Mode of being"
sections describe `study`, `submit`, `Site`, and the two OTA examples, but
were not updated when `hedloom.visualize` and the Dask-cluster variant of
`ota_pvt_clean.py` were added (commits `0c6d226` and `da2a606`, both after
whatever commit last touched `hedloom/ONTOLOGY.md`).

**What I did.** Nothing — the task scoped this pass to `docs/` content and
docstrings, and `ONTOLOGY.md` files were explicitly background reading
("Read ... each unit's ONTOLOGY.md ... before writing"), not a stated
deliverable. I did not want to guess at ontology-level language (mode of
being, evidence claims) under a docs-only mandate.

**Recommendation.** `hedloom/ONTOLOGY.md` should get a short addition recording
`hedloom.visualize` as a current contract and the Dask-cluster example as
`hedloom`'s own evidence that `submit(client=...)` really dispatches to
`hedloom_run.graph`, the next time someone is doing ontology-owning work on that
unit.

## 7. Left untouched: `docs/architecture.md`, `ONTOLOGY.md` files, `AGENTS.md` files

I read all of these as instructed but found no factually false claim in them
(unlike `hedloom-run/docs/index.md`'s Dask claim and `hedloom/docs/index.md`'s
emptiness, which were the two confirmed content defects named in the task).
`docs/architecture.md` (root) describes `composition.py`'s mechanics, which I
exercised directly while fixing the link/toctree warnings and found accurate.
