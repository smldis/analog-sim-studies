# Catalog of Proposed Changes to the Manifesto

This catalog proposes corrections to [the manifesto](../manifesto.md), not new
product goals. Each entry is deliberately separable so it can be accepted,
rejected, or annotated without implying acceptance of the others.

1. **Make deck-first sidecar composition the center, not parameterized studies**

   **Where:** “The center of gravity should be parameterized studies.”

   **Proposed change:** Replace this with a claim that the center of gravity is
   reviewable composition around an authoritative, already-working simulator
   directory. Treat parameters, corners, and study definitions as uses of that
   composition model, not as the primary differentiator.

   **Arguments:** The challenges document establishes that parameterized
   characterization is a mature category: CACE, Virtuoso ADE, PyOPUS, and
   spicelib all cover substantial parts of it. What is unusual in this project
   is the adoption boundary: copy ordinary simulator inputs, apply typed and
   source-traced transformations, and leave a materialized directory that can
   be inspected without translating the circuit into a new canonical schema.
   Moving that fact to the ideological center also resolves the tension between
   the manifesto's broad future framework and the repository's intentionally
   narrow preparation layer.

   **Real example:** CACE's current datasheet format already combines conditions,
   tool templates, measured variables, plots, and specification limits; its OTA
   tutorial uses a YAML datasheet and a CACE testbench template to characterize
   gain, unity-gain frequency, and phase margin. That is strong evidence that
   “parameterized studies” alone is occupied territory
   ([CACE datasheet format](https://cace.readthedocs.io/en/latest/reference/datasheet_format.html),
   [5T OTA tutorial](https://cace.readthedocs.io/en/latest/tutorials/ota_5t.html)).

   **Annotation:** CACE is awesome, however i looked at the internals and there is not much and its easily reiplementable to our liking, some naming is confusing, for example i saw some parameter datastructure actually handling simulations, isnt that weird?
   In any case the CACE approach on dependency handling of the whole verification flow is awsome and should be added to the scope of the manifest.

2. **Correct the opening question so it does not promise the broader stack**

   **Where:** “Should we build a Python package for defining, expanding,
   launching, and evaluating parameterized analog simulation studies in a
   reusable, text-based way?”

   **Proposed change:** Recast the question around preparing inspectable variants
   of existing analog simulation inputs. If launching and evaluation remain in
   the sentence, label them as adjacent possibilities rather than part of the
   package's defining claim.

   **Arguments:** The current sentence bundles four distinct systems—authoring,
   expansion, execution, and evaluation—and makes success in all four sound
   necessary. The manifesto later says not to build a cockpit or giant workflow
   engine, while the repository contract explicitly stops at preparation.
   Narrowing the opening is therefore a correction of scope and identity, not a
   proposal to remove a currently implemented capability.

   **Real example:** spicelib already pairs `SpiceEditor` with `SimRunner` for
   edited netlists, parallel runs, and result handling across LTspice, ngspice,
   QSPICE, and Xyce. A project whose headline includes launching must explain why
   it is not another runner/editor combination
   ([spicelib overview](https://spicelib.readthedocs.io/en/latest/readme.html),
   [SimRunner example](https://spicelib.readthedocs.io/en/latest/_modules/spicelib/sim/sim_runner.html)).

   **Annotation:** The manifesto is a vision, the opening statements have the corect scope, i would drop text-based and replace it with headless, since many times headless is good for reuse, latency tooling and agentic workflows. Bundling different systems is good if it follows the vision, we should make them moular, explicit, composable and individually usable both by an agent(preferably through cli interfaces) and by humans. Spicelib Is out due to licensing, i suggest we dont even look at its code to avoid GPL poisoning a more permissive codebase.

3. **Rewrite the “simpler claim” to state the actual differentiator**

   **Where:** “It is a text-first Python framework for reusable, parameterized
   analog simulation studies.”

   **Proposed change:** Say that it is a text-first Python preparation layer for
   making explicit, reviewable variants of existing simulator input directories.
   Avoid claiming templates, variation management, or result evaluation in this
   summary unless the claim is explicitly describing an aspiration rather than
   the package that exists.

   **Arguments:** A modest claim should be both distinctive and presently true.
   “Framework for parameterized studies” is still category language and obscures
   the strongest architectural commitment: the simulator-valid files remain
   authoritative. “Preparation layer” also prevents readers from inferring that
   the manifesto silently overrides the repository's no-launching,
   no-waveform-parsing boundary.

   **Real example:** Hdl21 makes circuits, generators, hierarchy, and parameters
   Python objects and exports netlists through VLSIR. It demonstrates why
   “Python + parameterized analog” does not distinguish this project; retaining
   an arbitrary Spectre/Eldo/ngspice directory as the contract does
   ([Hdl21 repository](https://github.com/dan-fritchman/Hdl21),
   [VLSIR repository](https://github.com/Vlsir/Vlsir)).

   **Annotation:** u can change the claim, it is supposed to be a target, not a claim. This is the scope of a manifesto. "It aims to be a ..." would be ok?. For the arguments would it be right to try to separate the strongest arch. committment from the main scope into a separate component (sidecaredits)? The component vision could still be part of the manifesto.
   For Hdl21 I love it, didnt know it. we should definitely keep track of existing tooling and approaches, even in the manifesto if they provide inspiration or architectural/implementation directions. VLSIR look like an implementation detail, not part of this scope right?

4. **Treat a working directory as an asset, not merely accidental reuse**

   **Where:** “The reusable unit should not just be ‘a directory that happened
   to work once.’”

   **Proposed change:** Keep the warning against undocumented copying, but
   acknowledge that a known-good simulator directory is valuable executable
   evidence and may properly remain the authoritative base. Define explicit
   reuse as named transformations and inputs around that base, rather than as a
   replacement for it.

   **Arguments:** The quoted phrase underrates the practical content of mature
   decks: proprietary directives, model includes, simulator scripts, encrypted
   models, and schematic-generated netlists can be difficult or unsafe to
   reconstruct in an intermediate representation. The sidecar model gains its
   low adoption cost precisely by preserving those details. The correction also
   makes “text-first” mean fidelity to runnable text, rather than privileging a
   new abstraction over proven inputs.

   **Real example:** PyOPUS's op-amp evaluation tutorial uses ordinary circuit
   fragments (`opamp.inc`, `topdc.inc`, and a model library) and then describes
   those files, simulator settings, analyses, and parameters in Python. Its
   concrete split shows that existing SPICE text can remain a useful,
   authoritative substrate even in a highly programmable flow
   ([PyOPUS performance-evaluator tutorial](https://spiceopus.si/pyopus/download/0.11.1/docsrc/_build/html/tutorial.evaluation.02-evaluator.html)).

   **Annotation:** the proposed change is weird sometimes I would  use a base just to have something to start with that execute without errors already, but later filled with the actual data to be used. we should avoid inserting these limit in the manifesto now at this early phase otherwise we risk missing opportunities. This concept of scoping and opportunitism  could be added to the manifesto, but i would try to avoid polluting the actual sections that should target clarity over verboseness. Maybe a final thoughs section or some other alternative to it fits the job.

   For Pyopus i really like the concept, we should avoid it due to licensing poisoning, if we would want to look at the source code we should ask the mantainer if he could consider releasing under APACHE2 / MIT.

5. **Qualify “templates” in favor of typed edits and small harnesses**

   **Where:** “users define templates and studies directly in text”; “testbench
   templates”; and “user-authored reusable templates” in the build-worthiness
   checklist.

   **Proposed change:** Use “small harness templates where needed” and make typed,
   explicit edits the default reuse mechanism. State that unrestricted template
   logic is not synonymous with text-first reviewability.

   **Arguments:** A template can be readable, but conditionals, loops, includes,
   and hidden substitution context create a second program whose rendered effect
   is not evident from a diff of the template alone. The current edit objects
   have narrower failure modes and carry source locations, which more directly
   serves the manifesto's inspection goal. This qualification preserves
   templating for concise harnesses without turning template expressiveness into
   an ideological good.

   **Real example:** CACE placeholders acquire meaning through names in the
   datasheet's conditions, and CACE documents Python-like expression handling in
   substitutions. This is effective for characterization, but the relationship
   between schema, expression, and emitted simulator input illustrates why
   templating needs an explicit boundary
   ([CACE template substitutions](https://cace.readthedocs.io/en/latest/reference/template_format.html),
   [CACE datasheet conditions](https://cace.readthedocs.io/en/latest/reference/datasheet_format.html#conditions)).

   **Annotation:** I am not sold on the change, the existing "templates" statements are proably ambiguos or wrong right  now, but they represent a real need that needs to be handled correctly in the manifesto without disrupting its essence, therefore I would avoid using current implementations and defaults as references for changes in the manifesto.

6. **Remove subjective commercial-tool claims from the factual premise**

   **Where:** “The commercial environments are powerful, but they are often
   heavy, sluggish, difficult to automate cleanly, and not especially good at
   making testbench reuse feel natural.”

   **Proposed change:** Reframe this as an adoption and representation critique:
   commercial environments can be capable and automatable while still binding
   reusable intent to proprietary databases, licenses, and GUI-centered project
   state. Present heaviness or sluggishness as user experience that varies by
   installation, not as the argument's factual foundation.

   **Arguments:** “Sluggish” is neither defined nor supported, and “difficult to
   automate” is too absolute given current scripting and regression facilities.
   The durable objection is inspectability and portability of the authored
   contract, where the manifesto has a coherent alternative. A fairer statement
   makes the comparison more credible without conceding the value of ordinary
   files and version-control review.

   **Real example:** Cadence documents ADE Assembler run plans usable
   interactively or through scripting, command-line regression generation,
   distributed simulation, multi-test management, corners, Monte Carlo, and
   specification reporting. The same product remains a Virtuoso environment,
   so its capabilities rebut the automation generalization while leaving the
   text-first portability critique intact
   ([Virtuoso ADE Suite datasheet](https://www.cadence.com/en_US/home/resources/datasheets/virtuoso-ade-suite-ds.html),
   [ADE Assembler product page](https://www.cadence.com/en_US/home/tools/custom-ic-analog-rf-design/circuit-design/virtuoso-ade-assembler.html)).

   **Annotation:** You  are wrong about Virtuoso ADE/ Studio, even if they have those features I can tell you their usability is currently very low due to user discomfort due to freezing, resource wasting, complex api. Reimplementing these features would better fit our users needs and also become free of charge.

7. **Bound study dependencies to named artifact relationships**

   **Where:** “What about simulation dependencies?” and “explicit dependency
   handling between studies” in the build-worthiness checklist.

   **Proposed change:** Retain dependencies only as a narrowly defined pressure:
   a study may consume a named, immutable artifact prepared elsewhere. Add a
   caveat that dynamic fan-out, adaptive loops, extraction orchestration, and
   general task scheduling are workflow-engine concerns rather than evidence
   that this package should own them.

   **Arguments:** The manifesto already fears becoming a workflow engine but
   gives dependencies equal checklist status without saying where the boundary
   lies. An artifact-level definition prevents a dependency from meaning
   anything from “read this operating point” to “run the whole physical-design
   flow.” It also fits deck-first preparation: an extracted netlist can be a
   pinned input without this package learning to operate the extractor.

   **Real example:** mflowgen already models parameterized graphs of sandboxed
   ASIC/FPGA steps with declared inputs and outputs, then emits Make or Ninja to
   move files and run them. That is useful architectural evidence for explicit
   artifacts, but also a concrete warning that owning arbitrary step execution
   is a separate product category
   ([mflowgen documentation](https://mflowgen.readthedocs.io/en/stable/)).

   **Annotation:** mflowgen is also inspiring, we should not be afraid to introduce a vision of something similar to it in one of our submodules, also CACE has a similar feature even if it is less dynamic. It is a narrow topic if we are looking at the manifesto top level, but it should be handled with care (if people built packages for it they probably had a good reason to do it, and i feel there is the need). I am not sure i understand your arguments about dependency and artifacts could you explain them?

8. **Make the cocotb analogy precise rather than broadly procedural**

   **Where:** “Why `cocotb` still matters as inspiration,” especially “programmable
   test logic” and “a clean mental model.”

   **Proposed change:** Keep cocotb as inspiration for Python-authored,
   reusable verification code, but say explicitly that the transferable unit is
   packaging and author experience—not coroutine timing semantics, live analog
   access, or a uniform simulator-control interface.

   **Arguments:** The manifesto already rejects simulator-hook equivalence, but
   “programmable test logic” can still invite readers to infer a live procedural
   analog testbench. Official cocotb documentation gives a sharper dividing
   line: standard digital interfaces do not directly expose the analog domain.
   Naming the non-transferable semantics makes the inspiration useful rather
   than atmospheric.

   **Real example:** cocotb's mixed-signal examples require HDL helper code
   because VPI, VHPI, and FLI cannot directly access the analog domain; the
   documented regulator probe was limited to Cadence Incisive/Xcelium with AMS.
   This is direct evidence for retaining the inspiration while refusing the
   mechanism
   ([cocotb mixed-signal documentation](https://docs.cocotb.org/en/development/mixed_signal.html),
   [regulator example](https://docs.cocotb.org/en/v1.8.0/regulator.html)).

   **Annotation:** ok

9. **Split competitors from architectural inspirations**

   **Where:** “What existing tools suggest,” including the single inspiration
   list containing cocotb, PyOPUS, BAG/BAG3++, Edalize, and mflowgen.

   **Proposed change:** Separate tools that establish competitive baselines
   (CACE, spicelib, PyOPUS, and commercial ADE) from tools that contribute one
   bounded architectural lesson (cocotb, Edalize, mflowgen, and BAG). Annotate
   each inspiration with the exact lesson and its non-goal.

   **Arguments:** The present list can imply that all tools validate the same
   analog-study concept. They do not: Edalize is primarily an EDA backend/flow
   abstraction with HDL-oriented metadata, mflowgen is an ASIC/FPGA build-flow
   graph, BAG is a broader programmable analog-generation methodology, and
   PyOPUS directly overlaps simulation and evaluation. Classification makes the
   intellectual lineage more honest and prevents “inspired by” from quietly
   broadening scope.

   **Real example:** Edalize describes tool-agnostic EDAM inputs and extensible
   tool/flow backends, while mflowgen describes sandboxed graph steps with
   explicit file interfaces. These earn their places specifically for adapter
   boundaries and artifact interfaces, not as proof of demand for another
   analog characterization framework
   ([Edalize overview](https://edalize.readthedocs.io/en/latest/),
   [EDAM API](https://edalize.readthedocs.io/en/latest/edam/api.html),
   [mflowgen documentation](https://mflowgen.readthedocs.io/en/stable/)).

   **Annotation:** be careful that tools like CACE have multiple of submodules that may fit this manifesto submodules, the mainfesto has a broader scope because it is a vision, all those tools can provide references, contributions, or even be part entirely of what we are targeting here. I am not expecting they would replace the current concept fully.

10. **Turn the build-worthiness checklist into comparative, scoped tests**

    **Where:** “A simple test for whether it is worth building,” especially
    parameter management, sweep/corner expansion, automation, dependencies, and
    measurement/spec evaluation.

    **Proposed change:** Require the proposed approach to improve a checklist
    item specifically for arbitrary existing decks through explicit,
    inspectable transformations; do not require superiority in every listed
    category. Mark execution, dependencies, and evaluation as out of the test
    when judging the preparation-only package.

    **Arguments:** As written, the checklist is both too broad and too easy to
    satisfy rhetorically: “better” has no user, baseline, or representation
    boundary. Several entries are already strengths of established tools, while
    demanding all of them would make the narrow package fail by definition.
    Scoping the comparison tests the manifesto's unique claim and prevents the
    checklist itself from becoming a roadmap.

    **Real example:** PyOPUS already supports SPICE OPUS, HSPICE, and Spectre,
    extracts measures such as gain, bandwidth, rise time, and slew rate, and
    evaluates corners, worst cases, Monte Carlo, and yield with parallelism.
    Therefore “measurement and spec evaluation in Python” is not by itself a
    meaningful build test; doing something reviewably useful to an unconverted
    working deck is
    ([PyOPUS documentation](https://spiceopus.si/pyopus/doc/index.html)).

    **Annotation:** I already have seen benefits with the existing sidecaredits module, so build worthiness is already a Yes. Analog sim studies is becoming a broader concept built on top of modules, we should be able eventually to map the checklist items to modules/submodules. This composition concept also helps to avoid a single roadmap

11. **Define repeatability at the preparation boundary**

    **Where:** “The output is ‘this study was defined, expanded, executed, and
    evaluated in a way that can be inspected and repeated.’”

    **Proposed change:** For the present manifesto, define the inspectable output
    as a materialized input directory plus the parameters and ordered edits that
    produced it. Do not imply that reproducible execution or evaluation follows
    from repeatable text preparation; simulator versions, model files, options,
    and external environment remain part of those stronger claims.

    **Arguments:** Recreating bytes is a valuable and achievable guarantee, but
    it is not the same as reproducing a waveform or pass/fail result. Analog
    simulations can depend on external model libraries, simulator revisions,
    numerical options, seeds, and licensed binaries. Separating these guarantees
    sharpens “text-first” and prevents provenance language from overstating what
    a copied and edited directory proves.

    **Real example:** PyOPUS documents simulator-specific differences even within
    its abstraction: its HSPICE adapter treats temperature specially, optimizes
    job ordering by topology, and does not support repeated parameter-swept
    analyses with collected `.measure` results. The same authored intent can
    therefore have backend-specific execution semantics
    ([PyOPUS HSPICE adapter](https://spiceopus.si/pyopus/doc/simulator.hspice.html)).

    **Annotation:** I would avoid reducing the scope, we can split the reduced scope of a module from the toplevel. However your argument about external data is not valid, we can always track their versions and provenance fro reproducibility or even save a local copy when needed. This is full reproducibility, we might then also add less exacts alternatives as needed that could go under the concept of repeatability or ligther reproducibility.
