# Target-path potential review

Read-only source review of the contract, Rust reduction and CLI composition,
independent Python checker, proof dispatch, and benchmark runner integration.
No concrete soundness or integration defect found in the reviewed snapshot.
No builds, tests, measurements, or remote commands were run by this reviewer;
this conclusion does not substitute for the separate test and build results.

## Checked reasoning

For each place, the unary constraints imply the selected integer upper bound.
Rust normalizes the divisor to positive and uses `div_euclid`; Python uses `//`.
Both compute floor(b/a), including negative quotients and `i64::MIN` inputs.
An inconsistent equality still implies that bound vacuously; it need not be
recognized separately for soundness. Missing bounds or decreasing transitions
skip the transform.

With B equal to the sum of those bounds and every transition delta nonnegative,
every successful original prefix has total at most B. Its slack is exactly
B minus that total. A successful next step therefore has enough slack to pay
its delta. Conversely, augmented firing preserves every original guard and
update. The original target rows remain unchanged apart from a trailing zero.
Initial total greater than B is a sound negative certificate, including when
all deltas are zero. Feasible constant-total candidates are skipped.

Rust checks incidence sums, bound sums, slack subtraction and witness sums;
u64 conversions reject unrepresentable slack or slack arcs. Widening i64/u64
before multiplication makes each witness product fit i128, while accumulation
is checked. Python validates the source integer ranges and reconstructs using
arbitrary-precision arithmetic with explicit representability checks.

Trap projection precedes potential augmentation. Positive lifting removes the
slack marking first, then maps trap-projected transition IDs back to the original
net; both steps replay the original guards and target. Negative nesting is
`trap(potential(inner))`, so each verifier reconstructs the right input for the
next verifier. Transition order, target-row order, bounds, and equality flags
are preserved. Slack-name collisions are resolved consistently.

## Proof and resource boundaries

- Minimal certificates have strict field sets and reconstruct the candidate;
  serialized bounds or augmented nets are not trusted. Reduction verification
  requires an accepted inner negative proof. Unsupported kinds fail Rust
  dispatch or Python dispatch; optimized Python is rejected. The module's
  `wrap_proof` and `verify_reduction` APIs alone do not validate an inner proof;
  recursive dispatch is the acceptance boundary.
- CLI lifting retains the existing engine proof, or wraps a legacy state-equation
  certificate. Reduced exhaustion without a certificate becomes Unknown.
  Missing/invalid lifting and lifting expiry also become Unknown, as contracted.
  Preparation failure falls back with only the remaining time.
- Both transforms use a preparation deadline of one tenth of their remaining
  budget, capped at 100ms, and a work cap of min(100*max_states, 20M). Verification
  shares a deadline and depth32 across reduction wrappers, but each layer has
  its own work budget. Some legacy leaf checkers enforce no internal shared
  deadline; the surrounding wrapper checks on return. Thus the deadline is not
  a preemptive CPU limit for those leaves. Bounded validator subprocess limits
  remain necessary; this is an existing resource boundary, not a false-proof
  finding.
- Runner flags are restricted to selected native original-input methods, command
  lines contain the requested flags, environment metadata records them, and the
  new checker source is included in runner provenance. No frozen runner or live
  experiment was changed by this review.

## Reviewed source identities

SHA256 values recorded at review completion:

```text
research/target-path-potential-contract.md 6c80e2dc891cee55c73f9d935153fb9c77b729d1c841e7a1896f9407e34d943d
src/target_path_potential.rs 35bfcb499aa43d61767e379ba1ab1de04bbca7280f94cb1cbf5683852ae757b9
src/main.rs cb8443bb072626b6d7db646b784e4b7cfcc6a376cbe5c262476d5171c1fda924
scripts/target_path_potential_checker.py a0f9464fc08fa4958264ca985a0303552cf7b4b839ef965ef8a4e42d3a24f500
scripts/benchmark.py 4ba0737ccdee2ba50315fffa144c6b7423e922051f7e64fdc0698d95865debce
scripts/benchmark_smpt_classic.py ba68a00fb8767efd7d351c0fadb7837be86a4798cf381b83845ee994100fffbf
```

No novelty or performance conclusion is made.
