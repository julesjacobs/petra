# Experimental target-path potential interface

The opt-in `--target-path-potential` flag tries the all-ones place weight vector.
It runs after target-zero trap projection when both flags are present. Defaults,
engine schedules, existing frozen binaries, and the running Linux application
comparison are unchanged. The flag conflicts with raw input and unlimited mode.

For every place, derive the tightest available upper bound from unary target
constraints. For a nonzero unary equality a*m=b, use floor(b/a). For a unary lower
inequality a*m>=b with a<0, use floor(b/a). Arithmetic is exact; flooring applies
to negative values too. Missing bounds skip the transform. Let B be their sum.
Check every transition has nonnegative total token change d. This proves every
prefix of any target-reaching execution has total tokens at most B. It is a
bound on successful paths, not on all reachable original markings.

If initial total exceeds B, issue a checked infeasibility proof. Otherwise,
when at least one transition grows the total, append a slack place initially
B-initial_total; each growing transition consumes d slack tokens. All original
arcs, transition IDs, target-row order and bounds remain; target coefficients
receive one trailing zero. The augmented net preserves total+slack=B. Every
original successful trace lifts to the augmented net; every augmented successful
trace projects to the original. Name collisions append underscores to
__target_path_slack. Constant total with a feasible bound skips the transform.

Checked i128 arithmetic suffices for this candidate; overflow or unrepresentable
u64 slack/arcs causes conservative fallback with only remaining time. Preparation
has a tenth-of-remaining-time budget capped at100ms and at most20M work units.
Witness lifting replays on the original net and checks original target truth.
Uncertified reduced exhaustion, failed lifting or expired lifting yields Unknown.
The shared CLI wrapper preserves nested trap/potential proof order.

Minimal certificates reconstruct the candidate rather than trusting serialized
weights, bounds, maps or augmented nets:

- {"kind":"target-path-potential-infeasible-v1"}
- {"kind":"target-path-potential-v1","inner":{...}}

Both Rust and independent Python check strict fields, original weighted arcs,
monotonicity, and target bounds. Reduction certificates additionally reconstruct
the augmented net and check its inner proof. A reduction alone proves nothing.
Existing depth32 and shared verification deadlines apply to nested reductions.
The Python dispatch rejects optimized Python because legacy leaves use asserts.

This is a checked preprocessing experiment, not a new complete reachability
procedure or a novelty/performance claim. Tests, source freeze and same-binary
ablation must precede any promotion. The planned screen retains all104 existing
development challenges and failures; it does not substitute for the separate
192-query application comparison or reserved-family evaluation.
