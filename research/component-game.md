# Checked component-choice search

The full twelve-source raw serializability development comparison improves from six solved sources to ten. Both configurations ran twice at a five-second input-inclusive limit with sampled 2 GiB process-tree memory. Every accepted answer was independently checked against the original Petri net and serial automaton. The six positives are preserved, and four new negatives are stable across both repetitions. Ring sizes four and five with pair locking remain unresolved.

Results: `research/raw-component-game-portfolio-v1-analysis.json`, with all 48 rows retained in `results/raw-portfolio-component-{before,after}-v1`. Read-only local capacity auditing overlapped this experiment, so it is developmental coverage evidence, not an isolated timing comparison. Publication timings require a later Linux repetition.

## Mechanism

The old discovery made a greedy component choice after each transition. A saved original-query trace demonstrated the failure: a reset could either move to a new component or be absorbed into a period of the current component. Greedy selection absorbed it; the next successful operation could not transfer, although another component choice permitted a closed invariant.

Discovery now builds a graph of candidate pairs of projected control markings and serial-language components. For each enabled projected transition it records all certified component transfers. A node survives exactly when every enabled transition has at least one surviving successor. Repeatedly removing failures computes the greatest fixed point, retaining mutually supporting cycles. A surviving initial node supplies one successor choice per transition and an ordinary component-invariant certificate.

Only proof discovery changed. The Rust and independent Python certificate checkers are unchanged. They check the original weighted net, initial inclusion, transition closure, and serial path-schema sublanguage. Resource exhaustion returns unknown; an incomplete graph is never accepted as a closed invariant.

A second observed failure involved unbounded accumulation of pending observers in the projected control state. Discovery now first attempts the empty control projection with one eighth of its work allowance. If this cannot yield a checked proof, it attempts the structural projection. This proves some response-language inclusions without enumerating pending readers. A failed first attempt conservatively reserves its entire allowance, including checker work. Control-vector copies are charged before allocation.

## Validation and limits

The full Rust suite passes: 304 tests, one pre-existing ignored test. Nine focused discovery tests cover reset choices, unsafe repetition, cyclic choices, universal transition obligations and unbounded pending requests. Clippy passes. Diagnostic proofs for the two failure mechanisms also pass the independent original-query checker.

Frozen implementation: `results/solver-component-game-v1`, including the complete source and vendor/varisat. Binary SHA-256: fa24c7ee15a01cfe83d9ab16a16e2944eb418630307f2be46b9cac4b8078c174. Source archive SHA-256: 1117fe41777ad68bd943df0d240c05b54ce4c013689dafefa5b9033c0bf504f0.

The method is incomplete: schema discovery, coefficient decomposition, control projection and resources still limit it. The graph fixed-point algorithm itself is standard; these results do not establish publication novelty, a complete VASS decision procedure, or superiority over competing tools. The application and external-suite comparisons remain separate.
