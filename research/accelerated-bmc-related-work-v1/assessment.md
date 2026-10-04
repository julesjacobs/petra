# Prior-art boundary for accelerated BMC

Read Crossref's publisher-supplied abstract and bibliographic metadata for Florian
Frohn and Jürgen Giesl, **Integrating Loop Acceleration Into Bounded Model Checking**,
Formal Methods (FM 2024), published 2024-09-11,
https://doi.org/10.1007/978-3-031-71162-6_4.
Metadata is preserved in crossref.json; OpenAlex's public open-access location
record is preserved in openalex.json. The full paper has not yet been read here.

The abstract explicitly describes tight integration of acceleration with SMT BMC,
adding shortcuts on the fly to find deep counterexamples, and blocking clauses
that can prove safety for examples where ordinary BMC diverges. It reports a
competitive unsafety evaluation and orthogonal safety behavior. These are the
paper's claims, not results reproduced in this project.

Consequences for our prototype:

- "BMC + acceleration" and adding shortcuts to find deep executions are not a
  sufficient novelty claim. Our exact fixed-word guard/effect encoding also
  implements established acceleration mathematics.
- Our current vocabulary is discovered statically and our driver restarts Z3 at
  each depth. Neither duplicates the claimed dynamic integration, nor establishes
  that a static vocabulary is competitive with it.
- We do not implement the paper's blocking clauses or any global-unreachability
  rule in this prototype. Bounded UNSAT remains unknown.
- Next inspect the full algorithm, its restrictions and implementation/artifact
  before deciding whether to adapt its refinement architecture or propose a
  Petri-net-specific improvement. Candidate contributions need both a precise
  difference and an ablation demonstrating why it matters.

The present finite benchmark screens evaluate practical ingredients only. They
do not establish novelty, a new decision procedure, or publication readiness.

## Subsequent primary-source inspection

Downloaded the open-access publisher PDF, saved with its SHA-256 and URL. Inspected
Sections3/4/6, with visual checks of complete PDF pages6and11 (printed78and83),
containing Algorithms2and3. This supersedes the abstract-only scope above for
these portions of the paper; no experiments were reproduced.

Important distinctions for implementation:

1. ABMC is incremental. It queries the error formula at the current bound using
   push/pop, then queries the extended prefix without that error formula. The
   satisfiable prefix model supplies a trace even when the target query is UNSAT.
   Our driver currently restarts and discards this opportunity at each depth.
2. Its dependency graph is built from observed consecutive syntactic implicants
   in feasible SMT traces. This differs from our static token-production graph,
   whose cycles need not correspond to any enabled execution.
3. Accelerated transitions are added as alternatives at the next unrolling step.
   Learned transitions can occur in traces, so nested acceleration is possible.
   Reaccelerating an already accelerated singleton is deliberately avoided.
4. Blocking clauses in Algorithm3 suppress the corresponding ordinary cycle at
   the current position and after choosing its acceleration. Stable cached IDs
   matter: assigning fresh IDs to the same acceleration can defeat those clauses.
5. Section4 explicitly requires exact acceleration for the safety claim with
   blocking clauses. With under-approximating acceleration, those blocking clauses
   remain useful for finding counterexamples but cannot justify safety. Our fixed
   Petri-word summary is exact, but that alone is not an implementation/proof of
   Algorithm3, especially for nested symbolic repetitions.
6. The paper evaluates integer linear-CHC benchmarks from CHC-COMP2023, using
   300s wall/1200s CPU/128GB limits. Those results do not directly compare with our
   1s/5s Petri-net screens. Its safety results are described as noncompetitive
   overall, despite some unique proofs; do not promise a general safety solution.

The publication's evaluation page links LoAT v0.7.0 source and release:
https://loat-developers.github.io/abmc-eval/
https://github.com/LoAT-developers/LoAT/tree/v0.7.0
Saved evaluation.html and loat-v0.7.0-release.json. The release advertises a
69,348,800-byte loat-static asset with no published GitHub digest. It has not been
downloaded, installed, executed, or treated as a verified baseline. Acquisition
must record a SHA-256 and the resolved source commit, then validate target encoding
and all capability/timeout behavior before measurement.

The linked Zenodo record response was saved as loat-artifact-metadata.json. Its
2,182,109,005-byte artifact.zip has upstream MD5
10eacb786027091778bf76a14d26b4c3 and resolves to record11954017. It was not downloaded.
The smaller pinned release may suffice for capability development; artifact and
release identities must not be silently equated.

Next architectural experiment: obtain feasible prefix models and learn exact
Petri-net words incrementally; compare against our frozen static vocabulary at
matched budgets. Do not add safety blocking until its coverage argument and an
independent negative-proof path are implemented and tested. This is a proposed
adaptation of published techniques, not a novelty claim.
