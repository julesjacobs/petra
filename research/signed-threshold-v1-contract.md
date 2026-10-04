# Signed-threshold invariant kernel v1

Research prototype following pro-pair-review-v1/answer.md, not a new completeness
or novelty claim. V1 is a supplied-invariant kernel. Do not count supplied proofs
as automatic solver coverage. No change to portfolio/default scheduling.

Certificate JSON (reject unknown certificate fields):

```
{"kind":"signed-threshold-invariant-v1",
 "forms":[[[0,"1"]],[[1,"1"]],[[0,"1"],[1,"1"]]],
 "clauses":[[{"form":0,"threshold":"3","negated":true}],
            [{"form":0,"threshold":"2","negated":true},
             {"form":1,"threshold":"1","negated":true}]]}
```

Each form is a sorted list of unique (place, signed decimal integer) pairs;
coefficients are nonzero, indices in range. Empty form denotes zero. Thresholds
are signed decimal integers. Exact BigInt arithmetic, no clipping. A literal
means a.m>=k when negated=false, otherwise a.m<k. Clauses have one or two
literals; invariant is their conjunction. Empty invariant allowed but cannot
exclude a satisfiable target. Multiple syntactically equal forms denote the same
linear form; the checker must canonicalize them, never assume their independence
for equality or order facts. Independence would only lose precision, but all
implementations should use the same canonicalization.

Schema validates original Problem before checking proof. Check initial clause
truth in the concrete initial marking. For EVERY original transition t and EVERY
clause C check Boolean UNSAT of I AND Enabled(t) AND NOT C(m+post-pre).
Guards contribute positive coordinate-threshold units for every weighted pre arc,
including reads. Pullback changes k to k-a.(post-pre) and retains polarity; NOT
C flips polarity of each pulled-back literal. Target exclusion checks I plus
positive literals for every original >= row, plus negated (a,b+1) for equality.
The target may contain signed rows and arbitrary conjunctions.

For each obligation build a sparse implication graph over the occurring atoms.
Clauses and units give ordinary 2-CNF edges. For each identical form, add adjacent
threshold-order edges (higher => lower) and contrapositives. Nonnegative forms
with k<=0 are true for every marking; nonpositive forms with k>0 are false. Zero
form satisfies both rules consistently. NO OTHER arithmetic correlation or
initial-state fact is admitted as a semantic axiom. Boolean UNSAT is sufficient;
SAT means unsupported proof, never a concrete witness. Distinct templates may
have unrealizable Boolean valuations; this is a sound overapproximation.

Reject if any initial/transition/target obligation fails or a resource deadline
expires. A clause with zero net change on both forms is self-preserved within
this single-mode invariant; this shortcut is valid but initial truth and target
exclusion must still be checked. Guards are still needed for nontrivial clauses.

V1 certificate contains retained invariant clauses only: both Rust and Python
recompute implication-graph contradictions independently rather than trusting
supplied paths. Path certificates and watched proof dependencies are deferred
optimizations, explicitly not implemented in this version. No finite monitor in
v1; no claimed subsumption of phase-pair. Kernel tests include weighted/unbounded
nets, read guards, zero/equality targets, signed forms, integer extrema, malformed
schema and mutations that break induction. Differential Boolean/finite-net checks
must verify semantic correctness before discovery or corpus measurements.
