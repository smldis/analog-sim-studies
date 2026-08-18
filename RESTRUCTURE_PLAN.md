# Restructuring Plan

Working document. Records decisions taken, the ordered operations, and the
decisions still open. Supersedes nothing in `MANIFESTO.md` or `ONTOLOME.md` —
where this plan changes those, it says so explicitly.

**Status:** Ops 0 through 4 COMPLETE on branch `hedloom-rename`.
**Date:** 2026-08-13

| Op | State | Commit |
|---|---|---|
| 0 — Preflight | done | `a334194` chore: preflight hedloom rename |
| 1 — Rename + re-nest | done | `6046e53` refactor: rename ass* to hedloom and nest flow/exec/run |
| 2 — uv workspace | done | `2726626` build: replace pythonpath hacks with uv workspaces |
| 3 — Manifesto rescope | done | this commit — docs: rescope manifesto for a domain-generic hedloom core |
| 4 — Repo splits | done | `0e98bee`, `a64825c`, `97fa314`, `00b2a3e`, `3d79556`, `b147e68`, `35b439d`, `567e558` |

Op 1 verification: `composition.py tree` resolves with `hedloom` parenting
`hedloom-{exec,flow,run}`; `py_compile` clean over all tracked `.py`; zero
`ass`/`ASS` residue in tracked sources. 31 files changed across the two passes.

**Worktree note.** Op 0.2 archived and removed `.claude/worktrees/`, which were
live git worktrees rather than stale copies. All three have since been restored
via `git worktree add` at their original commits (`e0a46a0`, `f083638`,
`8262d9c`), all clean. Backup retained outside the repo at
`../analog-sim-studies-worktrees-backup.tgz`. **Do not treat `.claude/worktrees/`
as disposable in later ops** — check `git worktree list` before touching it.

---

## Decisions taken

| Decision | Rationale |
|---|---|
| `ass*` renames to `hedloom` | "ASS" is unusable publicly. `hedloom` confirmed free on PyPI and uncontested on web search (Op 0.1). |
| Distributions stay separate — no merge into one | Keeps `flow`/`exec`/`run` as unit directories with `unit.toml` and `ONTOLOME.md` beside their code, which `composition.py:151-154` and `MANIFESTO.md:173` depend on. A single distribution wants `src/hedloom/{flow,exec,run}/`, stranding each ontology a level from what it describes. Note: with no index publication, the *independent installability* argument no longer applies — the structural one is what carries this. |
| `hedloom` becomes its own repo | Same treatment as the other units. Reverses the earlier "keep inline" position. |
| `flow` / `exec` / `run` stay as directories inside the `hedloom` repo | The four-way cluster is not split into four repos; it moves as one. |
| `study` is never renamed | Public API (`ass/src/ass/__init__.py:130`) and the manifesto's core concept (`MANIFESTO.md:62`). |
| All split repos stay local for now | Nothing is published yet. Local bare origins, own history preserved. |
| `analog-sim-studies` keeps its name for now | Widening deferred, recorded below. |
| Manifesto gets a slight rescope | `hedloom` is domain-generic but currently built for analog-sim-study use cases. |
| Workspace-only dependency resolution | Chosen over git-dependency URLs or index publication. |
| No index publication | Nothing goes to PyPI. Consumers, if any, install from path or git. Makes the workspace the *only* resolution mechanism, and leaves version numbers near-decorative. `[build-system]` blocks stay — editable installs need them. |

**Verification convention:** `py_compile` plus `composition.py` declaration
validation only. No test runs — verified by hand.

---

## Op 0 — Preflight

| | Step |
|---|---|
| 0.1 | **DONE 2026-08-13.** No longer a gate, since nothing is published to an index — but recorded: `pypi.org/simple/hedloom/` returns HTTP 404, and web search found no software, company, or trademark hits. The name still matters for GitHub and searchability when the repos are shared. |
| 0.2 | Delete the three stale `.claude/worktrees/` copies. Untracked, so harmless to git — but they hold ~120 files with old names and will pollute every grep and sed in Op 1. |
| 0.3 | Clean `ass-flow/build/`, `ass-flow/dist/`, all `*.egg-info/`, all `.pytest_cache/`. These carry stale `ass_flow` metadata that will resurrect old names. Confirm they are gitignored. |
| 0.4 | Tag the pre-rename commit for rollback. |

---

## Op 1 — Rename + re-nest (single atomic operation)

Merged because both rewrite the same ~300 files. Split apart, the same diff
gets reviewed twice. Runs before the workspace work so that structure is final.

### 1.1 Directory moves

```
git mv ass       hedloom
git mv ass-flow  hedloom/flow
git mv ass-exec  hedloom/exec
git mv ass-run   hedloom/run

git mv hedloom/src/ass           hedloom/src/hedloom
git mv hedloom/flow/src/ass_flow hedloom/flow/src/hedloom_flow
git mv hedloom/exec/src/ass_exec hedloom/exec/src/hedloom_exec
git mv hedloom/run/src/ass_run   hedloom/run/src/hedloom_run

git mv docs/vision/ass-flow-rebuild-main.md \
       docs/vision/hedloom-flow-rebuild-main.md
```

### 1.2 Text replacement — order is load-bearing

Longest tokens first, or the compounds get corrupted:

1. `ass_flow` → `hedloom_flow`, `ass_exec` → `hedloom_exec`, `ass_run` → `hedloom_run`
2. `ass-flow` → `hedloom-flow`, `ass-exec` → `hedloom-exec`, `ass-run` → `hedloom-run`
3. `\bass\b` → `hedloom`
4. `\bASS\b` → `Hedloom`; `ASS Flow` → `Hedloom Flow`

**On the bare-`ass` rule:** `\b`-anchoring is safe against `class`, `pass`, and
`assert` — the first two have a word character before the substring, `assert`
has one after, so the boundary assertion fails in all three. Verify on the
corpus before trusting it.

**Exclude:** `.git/`, `build/`, `dist/`, `*.egg-info/`, `.pytest_cache/`, `.claude/`.

**Never touch:** `study`, `Study`.

Approximate blast radius (worktrees excluded): ~299 files referencing
`ass_flow`/`ass_exec`/`ass_run`, ~640 lines with a bare `ass` token in
`.py`/`.toml`, ~29 markdown files with prose "ASS", ~14 files with
`Analog Sim Studies` / `analog-sim-studies`.

### 1.3 Structural declarations

- Root `unit.toml` children → `["hedloom", "sidecar-edits", "spice-canonical", "netlist-decomposition"]`
- `hedloom/unit.toml`: `id = "hedloom"`, and `children = []` → `["flow", "exec", "run"]`
  — this closes the gap where `ass/ONTOLOME.md` claimed "the three units beneath
  it" while declaring none
- Four `pyproject.toml` `name` fields
- `composition.py` and `docs/conf.py` string references

### 1.4 Verify

`python -m py_compile` over changed sources; **`python composition.py tree`** to
confirm the declaration tree resolves. The subcommand is required — bare
`python composition.py` exits 2 (`{tree,test,docs}` are the operations).
`composition.py:151-154` requires children be *immediate* child directories —
the new nesting satisfies this, and it is the assertion most likely to fail on a
wrong path.

### 1.5 Path strings are NOT covered by the text replacement

Learned the hard way in the first pass. After re-nesting, the token
`hedloom-flow` means two different things and only one of them is still correct:

- **Distribution name** (`dependencies = ["hedloom-flow"]`) and **unit ID**
  (`integration-tests/test_composition.py`) — still correct, must NOT be touched.
- **Filesystem path** (`ROOT / "hedloom-flow" / "src"`, `PYTHONPATH=hedloom-flow/src`,
  `../hedloom-flow/src`) — now WRONG; the directory is `hedloom/flow`.

Step 1.2 renames the token identically in both, so every path usage silently
breaks. Sweep for it explicitly:

```
grep -rnE '"hedloom-(flow|exec|run)"|/hedloom-(flow|exec|run)/|hedloom-(flow|exec|run)/src' .
```

Known sites: `integration-tests/test_ota_pvt_plan_reference.py`,
`studies/rc_corners.py`, `studies/ota_pvt_clean_nested.py`,
`hedloom/pyproject.toml`, `hedloom/README.md`, `README.md`, and three files
under `docs/reference/ota-pvt-plan/`.

**This trap recurs in Op 4** — every repo split moves directories, so any path
string pointing at a moved unit needs the same sweep.

---

## Op 2 — uv workspace

Removes the sibling-path hacks that would otherwise leave each split repo
broken when cloned alone.

Two workspace roots, not one. `hedloom` owns its own so that it works standalone
after Op 4d; the parent excludes that subtree and reaches it by path.

Create a root `pyproject.toml` (none exists today):

```toml
[tool.uv.workspace]
members = ["spice-canonical", "netlist-decomposition", "sidecar-edits"]
exclude = ["hedloom"]

[dependency-groups]
dev = ["hedloom", "spice-canonical", "netlist-decomposition", "sidecar-edits"]

[tool.uv.sources]
hedloom               = { path = "hedloom" }
spice-canonical       = { workspace = true }
netlist-decomposition = { workspace = true }
sidecar-edits         = { workspace = true }
```

No `[project]` table — verified 2026-08-13 that uv accepts a virtual workspace
root, so the composition root does not have to pretend to be a Python package.
This also settles where dev dependencies go: without `[project]` there is no
`[project.optional-dependencies]`, so `[dependency-groups]` is the only form.

**Retire `requirements-dev.txt` into the dev group.** Current contents:

```
-e ./ass-flow[dask]      -e ./spice-canonical
-e ./netlist-decomposition   -e ./sidecar-edits[docs]
build  pytest  setuptools>=69  wheel
```

Note it never installs `ass`, `ass-exec`, or `ass-run` — the root dev
environment has no editable install of three-quarters of the hedloom cluster,
which is exactly what the `pytest` `pythonpath` entries are compensating for.
Op 2 removes a workaround rather than swapping one mechanism for another.

The `[dask]` extra on `ass-flow` moves into `hedloom`'s own repo: the parent
should not reach past its own `exclude` boundary to set extras inside a subtree
it does not own, and `hedloom` needs those declarations to work standalone.

Create `hedloom/pyproject.toml`'s workspace table:

```toml
[tool.uv.workspace]
members = ["flow", "exec", "run"]

[tool.uv.sources]
hedloom-flow = { workspace = true }
hedloom-exec = { workspace = true }
hedloom-run  = { workspace = true }
```

**Write this shape now, before the splits.** It is purely a directory
arrangement — git is not involved — so the configuration written here survives
Op 4d unchanged and needs no rework at split time.

Delete every `pythonpath` entry, keeping `testpaths`:

| File | Current value |
|---|---|
| `hedloom/pyproject.toml` | `["src", "../ass-flow/src", "../ass-exec/src", "../ass-run/src"]` |
| `hedloom/run/pyproject.toml` | `["src", "../ass-exec/src"]` |
| `netlist-decomposition/pyproject.toml` | `["src", "../spice-canonical/src"]` |
| `hedloom/flow`, `hedloom/exec`, `spice-canonical`, `sidecar-edits` | `["src"]` each |

**Risk:** pytest currently finds packages *only* via those paths. After removal
it depends on `uv sync` having editable-installed the members. Confirm before
proceeding to Op 4.

### Why `hedloom` is configured differently from the other three

It is the only split unit that *contains* workspace members. `sidecar-edits` and
`spice-canonical` are single-package repos needing no workspace at all standalone;
`netlist-decomposition` is also single-package, and its dependency lives in a
*sibling* repo, so under workspace-only it is simply not standalone-installable
(an accepted consequence, not a nesting problem). `hedloom` holds four
distributions whose dependencies are internal — so it can be fully self-sufficient,
and should be, being the generic core.

**Verified empirically 2026-08-13** (uv 0.x, scratch scaffold):

- Listing `hedloom` and its members in one parent workspace **fails**:
  `error: Nested workspaces are not supported, but workspace member has a
  tool.uv.workspace table`. This constraint is not in the uv documentation.
- `hedloom` as its own workspace root resolves standalone.
- Parent with `exclude = ["hedloom"]` plus `hedloom = { path = "hedloom" }`
  resolves cleanly, picking up `hedloom-flow` transitively without listing it.

**Rejected alternative.** `hedloom` can instead use plain path sources
(`hedloom-flow = { path = "flow" }`) with no workspace table; this also resolves
standalone. It was not chosen because workspace members are editable by default
and share one lock, which is what four co-developed distributions want. Note the
two mechanisms cannot be mixed: if the parent lists the subtree as members while
`hedloom` uses path sources, uv fails with *"included as a workspace member, but
references a path in `tool.uv.sources`"*. Either way the parent must `exclude`
the subtree and reach `hedloom` by path.

**Completion findings (`2726626`).** The root lock initially exposed a Python
version conflict: the virtual workspace covered sibling units that honestly
support Python 3.10 while its dev group also installed `hedloom`, which requires
Python 3.11. The fix was:

```toml
[tool.uv.dependency-groups]
dev = { requires-python = ">=3.11" }
```

This constrains only the dev group. The composition root remains a virtual,
non-package workspace root, and `sidecar-edits`, `spice-canonical`, and
`netlist-decomposition` retain their honest `requires-python = ">=3.10"`
declarations. Adding `requires-python = ">=3.11"` through a root `[project]`
table was rejected because it would force the whole workspace to Python 3.11
and introduce a phantom root package.

The same operation added `.toolchain/uv-cache/`, `.venv/`, and
`.pytest_cache/` to `.gitignore`. `UV_CACHE_DIR` is set project-locally to
`.toolchain/uv-cache` because uv's default `~/.cache/uv` is outside the
sandbox.

---

## Op 3 — Manifesto rescope

Prose only, small.

`MANIFESTO.md` is an analog-design vision, but `hedloom`'s three sub-units
describe themselves with zero analog content — "executor-neutral static
operation and flow planning", "durable attempt identity and reconciliation",
"walk a validated Plan and execute its invocations". The analog work lives
entirely in `spice-canonical` and `netlist-decomposition`.

- Add language admitting a domain-generic execution core that currently serves
  analog use cases first
- Update root `ONTOLOME.md` to match
- `hedloom/ONTOLOME.md`'s "the three units beneath it" becomes literally true
  after Op 1.3
- Record the deferred widening of `analog-sim-studies` inside the document, so
  the deferral is written down rather than forgotten

---

## Op 4 — Repo splits

All four units leave `analog-sim-studies`, which becomes a pure composition
root holding four submodules. All origins are **local bare repos** for now;
history is preserved in every case.

| | Unit | Precondition | Why this position |
|---|---|---|---|
| 4a | `sidecar-edits` | Op 2 | Zero internal coupling. Lowest-risk pilot — proves extraction, submodule wiring, and `composition.py` traversal end to end. |
| 4b | `spice-canonical` | Op 2 | No internal dependencies. Must precede 4c. |
| 4c | `netlist-decomposition` | Op 2, 4b | Depends on `spice-canonical`; its `../spice-canonical/src` path assumes monorepo layout. |
| 4d | `hedloom` | Op 1, Op 2 | Largest — four distributions and its own workspace root. Do last, with the lessons from 4a–4c. Op 2 already leaves it in final shape, so no workspace changes are needed here. |

### Per-unit procedure

1. Extract with history: `git filter-repo --subdirectory-filter <dir>` into a
   fresh clone (alternatively `git subtree split -P <dir>`)
2. Push into a local bare origin, e.g. `/home/smldis/working/AI/repos/<name>.git`
3. Remove the directory from the parent
4. `git submodule add <local-url> <path>`
5. Verify `python composition.py` still resolves the tree

`composition.py` contains zero git references — it resolves children purely as
filesystem paths, so submodules are transparent to it.

Re-pointing to public remotes later is `git remote set-url` plus a `.gitmodules`
edit — cheap, and deliberately deferred.

### Completion findings

Op 4 completed on 2026-08-13. The extracted repositories retain their unit
history on `main` in these local bare origins:

- `/home/smldis/working/AI/repos/sidecar-edits.git`
- `/home/smldis/working/AI/repos/spice-canonical.git`
- `/home/smldis/working/AI/repos/netlist-decomposition.git`
- `/home/smldis/working/AI/repos/hedloom.git`

Each unit used two focused superproject commits: remove then wire the submodule.
In operation order those commits are `0e98bee` / `a64825c`, `97fa314` /
`00b2a3e`, `3d79556` / `b147e68`, and `35b439d` / `567e558`.

Three local-origin details were not visible in the original procedure:

- `git rm -r` removes tracked files only. Ignored build artifacts can leave the
  path occupied, so each path required an inspected, unit-scoped
  `git clean -xfdn <path>` followed by `git clean -xfd <path>` before
  `git submodule add`.
- Local submodule clones require `protocol.file.allow=always`. It is set in this
  superproject's repository-local Git configuration; the submodule-add commands
  also needed the per-command `-c protocol.file.allow=always` form because the
  local setting did not propagate into the nested clone in this environment.
  A fresh clone using these local URLs must make the same allowance before
  `git submodule update --init`.
- `git init --bare` initially points `HEAD` at `refs/heads/master`, while these
  splits push `main`. Every bare origin must explicitly set `HEAD` to
  `refs/heads/main`; otherwise submodule checkout fails with `You are on a
  branch yet to be born`.

`hedloom/examples/_runs/` is ignored, untracked run evidence cited by the
Hedloom ontology, including durable attempt journals and example reuse state.
It therefore was not part of the extracted history. It was preserved across
the path cleanup and restored from
`/home/smldis/working/AI/hedloom-example-runs-backup.tgz`; it remains unstaged
inside the Hedloom submodule. The root `uv lock`, `uv sync`, import smoke check,
and `composition.py tree` all continued to work with submodule directories.

---

## Deferred decisions

| Item | Note |
|---|---|
| `spice-canonical` / `netlist-decomposition` naming | Not good public repo names. Must be renamed before either is published. Local-only until then. |
| `analog-sim-studies` naming | Needs widening to match the broadened scope. |
| Public remotes | None until the names above are settled. |
| Splitting `flow`/`exec`/`run` into their own repos | `MANIFESTO.md:160` says components are nested Git subrepositories, which strictly would want this. Deliberately not done: `open-concepts.md:35` records those boundaries as still-open hypotheses, and submodule pointer bumps would make moving code across them expensive during the prototype phase. |

## Out of scope

- Merging the four distributions into one
- Renaming `study`, or the `flow` / `exec` / `run` sub-unit names
- Any test-suite changes
