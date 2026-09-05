# Philosophical review: manifesto, Hedloom, and its ontolomes

Date: 2026-09-05. Status: advisory review; no architectural decisions adopted.

Manifesto alignment baseline: composition root `e0b547c`, Hedloom checkout
`3d0f5c4`. The original implementation review used root `c960348`; only
`MANIFESTO.md` changed between those root revisions, and the Hedloom checkout
is unchanged. This revision aligns the assessment with the adopted manifesto.
This is a dated design record, not a replacement for maintained contracts.
The review covers the root manifesto and ontology, Hedloom, and its Flow,
Exec, and Run children. It does not audit the other domain components.

## Judgment

The current [manifesto](../MANIFESTO.md) gives the project a clear purpose:
make engineering effort accumulate as accessible, reusable, and revisable
knowledge. Headless access, Python, preserved evidence, and composition serve
that purpose. They are means whose usefulness can be tested, while present
component boundaries remain open to revision.

It also addresses several concerns raised by the original review. It separates
computation from engineering conclusions, distinguishes kinds of
reproducibility, and gives prototypes latitude to explore. Structure and
verification should earn their cost through the work they support. The
manifesto now supplies reasons for judgment without prescribing an architecture
or a decision procedure for every open question.

The remaining tension is principally in the ontolomes' stronger claims: a
declared dependency can read as everything a result depends on, an execution
result as a conclusion, or a component exclusion as an absolute that its own
implementation contradicts. Clarifying these claims would bring current
contracts closer to the manifesto's account of trustworthy evidence and
revisable responsibilities.

The following suggestions are opportunities for useful clarification and
learning, not prerequisites for further development. A lightweight experiment
need not preserve every dependency or formalize every decision. More durable
commitments become worthwhile when a result is reused, shared, or relied upon
and the missing context affects that use.

## What the current manifesto has already resolved

| Earlier concern | Current position | Remaining work |
| --- | --- | --- |
| Execution and conclusion could be conflated. | [Carry the inquiry forward](../MANIFESTO.md#carry-the-inquiry-forward) explicitly treats computation as evidence and conclusions as dependent on interpretation, assumptions, and criteria. | Clarify the narrower meaning of Hedloom's `Study` and `run.value`. |
| Reproducibility lacked a clear object. | [Make evidence trustworthy and reusable](../MANIFESTO.md#make-evidence-trustworthy-and-reusable) distinguishes exact artifacts, procedures, and conclusions under stated conditions. | Describe which of these current records support when that distinction matters to their use. |
| Present components could become the presumed final architecture. | [Compose capabilities around real needs](../MANIFESTO.md#compose-capabilities-around-real-needs) explicitly permits combining, separating, replacing, and retiring components. | Use actual workloads to assess boundaries; keep adopted contracts accurate as they change. |
| Review and preservation could impose excessive ceremony on prototypes. | [Learn what deserves to be built](../MANIFESTO.md#learn-what-deserves-to-be-built) weighs structure against time, attention, computation, and learning. | Apply the probes below selectively, according to the uncertainty and consequence at hand. |
| Agent autonomy could be framed mainly as a constraint. | [The environment we work in](../MANIFESTO.md#the-environment-we-work-in) values agents' ability to make experiments and alternatives affordable, alongside human work and conventional automation. | Preserve latitude for exploration; additional review should have a concrete purpose rather than follow merely from agent participation. |

These positions are adopted manifesto guidance, not proposed changes from this
review. The broader vision remains intact; the implementation observations
below describe its current expression and limitations.

## 1. The manifesto's study is an inquiry; Hedloom's Study is an execution envelope

**Observed.** The [manifesto](../MANIFESTO.md#carry-the-inquiry-forward)
includes intent, context, actions, evidence, and decisions, and allows the
question itself to evolve. [Hedloom's ontology](../hedloom/ONTOLOME.md)
describes a named join between authored operations and execution.
[`Study` and `StudyRun`](../hedloom/src/hedloom/study.py) represent a Plan, its
execution namespace, and its outcomes. Calling `run.value` a "conclusion" does
not supply an account of why that value supports an engineering judgment.

**Assessment.** The manifesto now explicitly distinguishes a completed
computation from an engineering conclusion. Hedloom is a legitimate narrower
implementation, but its shared vocabulary should make that distance clear.
A successful execution can produce evidence against a hypothesis.
A correctly evaluated specification failure is knowledge, not necessarily an
execution failure. Reusing or pinning a result is neither accepting its
scientific interpretation nor approving a design.

**Proposal.** Say explicitly that the current `Study` implements the executable
part of the wider study concept. Keep execution outcome, evaluation verdict,
and accepted conclusion distinct. Leave ownership of the wider inquiry open
until a useful slice requires it; do not introduce a new lifecycle framework
merely to fill the vocabulary.

**Cheapest probe.** Follow one reported conclusion back through its criterion,
assumptions, evidence, and producing operations. Mark which links are durable
and which require the author's memory. The missing links define the next
useful preservation work more precisely than another general abstraction.

## 2. An ontolome needs to distinguish commitments from observations

**Observed.** The manifesto describes ontolomes as responsibilities and
commitments whose boundaries remain revisable. The [root ontology](../ONTOLOME.md)
calls runnable components hypotheses about architecture. Its child ontologies
mix purpose, present contracts, empirical evidence, exclusions, and historical
explanation.

**Assessment.** This is productive if disagreement remains possible: an
implementation can violate its contract, and evidence can challenge a boundary.
It becomes circular if whatever the code currently does is automatically what
the component ought to be. A passing example supports a bounded claim; it does
not prove the boundary optimal or the mechanism generally correct.

**Proposal.** Read each ontolome as an explicit, revisable semantic contract
with evidence attached. Separate four kinds of statement: chosen commitment,
observed capability, required assumption, and open hypothesis. A bug does not
silently revise a commitment; a deliberate boundary change revises both the
contract and its rationale. These distinctions can be expressed in ordinary
prose where ambiguity matters; they do not require a new document schema or a
classification exercise for every edit.

This also clarifies composition. Filesystem containment alone grants no
authority, but the root does explicitly own integration contracts. Those
statements can coexist: authority comes from the declared contract, not from
being higher in the directory tree. Shared vocabulary likewise need not be
duplicated into every child.

**Cheapest probe.** Classify the strongest sentence in each ontolome using
those four categories. If a sentence fits several, split it before extending
the implementation around it.

## 3. Portability and reproducibility need an explicit object

**Observed.** The manifesto connects files, discoverability, and retrieval to
[operator control](../MANIFESTO.md#keep-engineering-work-under-the-operators-control).
Its [evidence section](../MANIFESTO.md#make-evidence-trustworthy-and-reusable)
already distinguishes exact artifacts, procedures, and engineering conclusions,
while allowing lightweight experiments before fuller preservation. The current executor
records addresses and metadata, retains records after eligible workspace
removal, and provides separate pin and verification operations.

**Assessment.** Files are a useful representation choice; they do not by
themselves establish independent interpretability, available dependencies, or
repeatable results. A preserved manifest can explain a result whose payload
has been deleted. Repeating a procedure, recreating bytes, and reaching an
equivalent engineering conclusion are different achievements.

**Proposal.** Apply the manifesto's existing distinction to preservation and
reuse contracts where callers rely on them: state what can be reproduced and
under which recorded conditions.
Distinguish preservation of the account from preservation of the payload.
Reclaiming bytes need not conflict with the vision, but a surviving record
should not promise recoverable artifacts when only an account remains.

**Cheapest probe.** Choose one reference conclusion and attempt its reconstruction
using only the recorded package of evidence. Missing tools or context identify
the limits of that package, not a reason to narrow the vision.

## 4. Static Plans do not imply a statically known whole submission

**Observed.** [Hedloom](../hedloom/ONTOLOME.md) says a body cannot acquire
scheduling authority. [Run](../hedloom/run/ONTOLOME.md) nevertheless supports an
invocation submitting a further Plan. The current
[`live_source.refresh`](../hedloom/examples/live_source.py) actually calls
`live_session().submit(reading_study())` from an operation body.
The [open-concepts register](../docs/vision/open-concepts.md) also describes
staged authoring from previously produced values.

**Assessment.** Each child Plan can be complete before its own execution while
the parent Plan does not enumerate the work that child will contain. These
are different levels of inspectability. Staging does not automatically mean
adaptive search, but making every stage static does not by itself exclude
result-dependent orchestration between stages either. A body submitting a
child also plainly initiates more work, even if the kernel retains readiness
decisions within that child.

The current manifesto asks that an engineer be able to examine proposed work;
it does not require the whole evolving inquiry to be enumerated before any
execution. The unresolved issue is the scope of Hedloom's contract, not a
manifesto prohibition on staging or an authorization for adaptive control.

**Proposal.** State whether the inspectability promise applies per Plan or to
the transitive work of a submission. If nesting remains supported, describe
its initiation authority and parent/child provenance explicitly. Distinguish
static flow composition, staged Plan authoring, and adaptive decision-making.
Do not resolve their differences merely by reserving one prohibited name.

The [September 4 review](../hedloom/design/rearchitecting-nested-studies-2026-09-04.md)
already raises whether nesting earns its costs. That is prior inquiry, not
evidence of current implementation and not authorization to redesign it.

**Cheapest probe.** Compare the outer Plan with the actual invocations launched
by the live-source example. State which work was inspectable at each boundary
and which durable record links the boundaries. Use a real workload to decide
whether the additional authority deserves a first-class contract.

## 5. Reuse identifies a declared computation, not all causes of its result

**Observed.** [`input_digest`](../hedloom/exec/src/hedloom_exec/reuse.py) hashes
nine declared keys. The [Exec ontology](../hedloom/exec/ONTOLOME.md) both calls
reuse "sound by construction" and acknowledges undeclared dependencies.
[`_implementation_of`](../hedloom/flow/src/hedloom_flow/authoring.py) fingerprints
the function's source; it does not recursively fingerprint called helpers,
imported packages, or external executables. Source-file fingerprinting has a
documented size/mtime fallback above 64 MiB in
[`site.py`](../hedloom/run/src/hedloom_run/site.py).

**Assessment.** The digest establishes equality under the chosen declaration
scheme. The stronger claim that equal identities imply equivalent results
also needs complete dependencies, suitable determinism, faithful binding, and
stable evidence. A hash cannot establish those premises. A function-source
fingerprint improves coverage while leaving behavior outside that source
uncovered.

The same distinction matters over time: the façade fingerprints a source and
then passes its path to a body. That connects identity and location, but does
not freeze the bytes until consumption. Concurrent mutation is an untested
failure scenario in this review, not a reproduced defect.

**Proposal.** Put the conditional reuse claim beside the guarantee rather than
only in exclusions. Name the record identity as identity of a declared
computation, and distinguish it from identity of output content. State the
stability assumption for externally mutable sources and the weaker large-file
fingerprint explicitly.

**Cheapest probe.** Change a helper or tool version without changing the
operation source, then identify the declaration that must change for reuse to
remain justified. Separately test source mutation between identification and
reading if that scenario occurs in actual use.

## 6. Placement independence and kernel equivalence are conditional contracts

**Observed.** Placement is excluded from result identity. The code even
documents that a local debugging run may populate records later reused on a
farm. Run's ontology says the kernel changes only duration, then explicitly
permits different completed work when stopping on failure. Nested capacity
refusal is another graph-specific condition.

**Assessment.** Changing a queue can be operationally irrelevant to result
meaning; changing an execution environment need not be. Whether a resource
choice changes results is a property of the operation and its dependencies,
not something established by calling the choice "placement."

Similarly, successful deterministic invocations can agree across kernels
without the kernels admitting every same workload or producing identical
partial reports after failure. Replacement has a meaningful equivalence
contract only if its observables and preconditions are named.

**Proposal.** Promise the same identities and equivalent successful values for
supported workloads under equivalent declared environments. State failure,
capacity, and admission differences alongside that promise. Preserve the
separation between semantic dependencies and operational resource requests,
while allowing an author to declare environment facts when they affect meaning.

**Cheapest probe.** Keep the existing cross-kernel identity/reuse tests and the
controlled failure tests as separate evidence. Neither substitutes for the
other. Establish an explicit environment declaration in one workload that
actually depends on it before calling placement independence universal.

## 7. Refusal is a valuable principle, but its boundary is uneven

**Observed.** The agent guidance says an incomplete surface must refuse rather
than return plausible stale results. Yet
[`plan_bundles`](../hedloom/exec/src/hedloom_exec/planned.py) accepts omitted
source fingerprints, and a current test deliberately demonstrates that an
in-place source edit is then invisible. The Hedloom façade supplies
fingerprints; the narrower public APIs can still be used without them.

**Assessment.** Trusting a caller can be an explicit low-level contract. It is
not equivalent to guaranteeing that every supported use refuses when identity
is insufficient. The distinction matters because independent usability is
part of what earns these component boundaries.

**Proposal.** Distinguish a declaration-only primitive from a path that supplies
source fingerprints, with explicit preconditions for each. Fingerprinting
alone does not establish all the conditions identified in section 5.
If declaration-only addresses are
intended to be immutable or externally versioned, say so. Decide from actual
callers whether missing evidence should cause refusal or require an explicit
weaker mode. This review does not change those APIs.

**Cheapest probe.** Trace one independent Exec or Run caller with an external
source and identify who is responsible for establishing its immutable version.

## 8. Current ownership statements need reconciliation

These are observed textual inconsistencies, not proposals for new components:

| Surface | Inconsistency | Appropriate clarification |
| --- | --- | --- |
| Root ontology | Describes the Flow-to-Exec document contract as schema 2; current Flow emits 3 and Exec accepts 2 and 3. | State producer and consumer contracts separately. |
| Root and Exec ontologies | Say direct submission has never reached a real cluster; Hedloom records a real sequential smoke run. | Reconcile the account against recorded farm evidence; do not infer broader farm validation. |
| Hedloom ontology | Owns a durable study name, then excludes ownership of "identity" without qualification. | Distinguish study namespace, authored invocation, record, try, and artifact identity. |
| Run ontology | Owns `cluster_for`, Site sizing, and nested capacity handling; exclusions say it neither creates nor sizes clusters. | Separate cluster construction from the Session's lifetime ownership. |
| Run ontology | Excludes every transport; `hedloom_run.pooled.LSFPooledTransport` exists and is documented. | Name the pooled exception and the reason for its owner. |
| Exec ontology | Excludes content-digest verification; its pin contract includes inventory digests and verification. | Distinguish ordinary artifact capture from explicit pin verification. |

The philosophical point is that "one responsibility" means one coherent
purpose with explicit contracts, not a prohibition on every mechanism another
unit also uses. These distinctions let ownership remain precise as the
prototype learns.

## What deserves attention next

The current manifesto supplies the broader direction this review previously
asked to clarify. No further manifesto rewrite follows from the remaining
findings. The practical opportunity is to make the ontolomes express their
current commitments with the same care, starting with misleading guarantees
and the observed ownership inconsistencies above.

For deeper questions, choose a workload where an engineer has to reconstruct
context, doubts a reused result, or struggles across a component boundary.
Use the relevant probe to discover whether a small clarification, a capability,
or a changed boundary would help. The probes are optional starting points,
not an ordered approval process. Their value lies in what they reveal and the
effort they save; a question need not be settled before an unrelated useful
experiment proceeds.

Keep execution outcomes and engineering conclusions distinct, qualify reuse
and equivalence where callers rely on them, and leave wider inquiry ownership
open until use supplies a reason to choose. This preserves both trustworthy
evidence and the latitude to act, fail, and change direction that the manifesto
now explicitly values.

No canonical text was rewritten by this review. No previously recorded human
decision was changed. The open questions above are separable; accepting one
does not imply acceptance of a redesign or a new subsystem.

## Verification and limits

The original review inspected the then-current manifesto, root and four Hedloom ontolomes, applicable agent
guidance, unit declarations, READMEs, the Exec decision ledger, relevant
planning/design history, and selected current source and tests. Historical
notes informed the questions; current source and contracts support the
implementation observations. External philosophical attribution and a
competitive-tool survey were outside this review.

For this alignment, reread the adopted manifesto, root ontology, root guidance,
README, and unit declaration, and checked Git status and revision differences.
The root revision difference changes only the manifesto; the Hedloom checkout
remains at the original reviewed revision with a clean working tree. The
implementation findings are retained from that review, not presented as a new
code audit. The separate manifesto revision proposal is not the authority for
this alignment.

The original review ran a focused selection over all four unit test directories:

```console
PYTHONPATH=src:flow/src:exec/src:run/src python -m pytest -q \
  tests exec/tests run/tests flow/tests -k \
  'test_the_graph_kernel_produces_the_same_identities_as_the_loop or test_a_result_recorded_by_one_kernel_is_reused_by_the_other or test_stopping_cancels_the_unstarted_and_waits_for_the_in_flight or test_without_a_fingerprint_an_edit_is_invisible or test_an_implausibly_large_source_says_how_it_was_identified or test_a_nested_run_whose_waiters_hold_every_unit_is_refused or test_a_nested_run_with_one_unit_to_spare_is_admitted or test_placement_does_not_participate_in_identity or test_an_unchanged_document_reuses_the_inner_plan or test_a_changed_document_invalidates_everything_below_it or test_the_plan_is_complete_before_anything_is_spent or test_body_edit or test_implementation'
```

Original result: **12 passed, 3 skipped, 612 deselected**. Tests were not rerun
for this prose-only alignment. This supports the selected
local behaviors, not full-suite health or any new real-farm claim. The helper
change and concurrent source-mutation scenarios above were not executed.

The interface exposed no model/effort status line to independently verify the
global model-check instruction; that limitation was disclosed before inspection.
