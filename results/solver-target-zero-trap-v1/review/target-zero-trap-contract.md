# Experimental target-zero trap interface

Frozen comparison binaries and Linux runners remain unchanged. This candidate uses
an opt-in `--target-zero-trap` CLI flag before existing preprocessing/portfolio
search. No default schedule changes. Preparation work and deadline exhaustion fall back to
the existing solver on the original problem using only remaining time. A lifted
answer that cannot be checked within its deadline/work budget returns Unknown.

Seed forced-zero coordinates from bound-zero constraints: a same-sign equality,
or a nonpositive-coefficient lower inequality. Zero coefficients contribute
nothing; mixed signs give no zero fact. Validate original dimensions/arcs first.
Compute the greatest trap contained in this seed, using original positive-weight
arcs. A trap means any transition consuming from it also produces into it.
If initially marked, the target is impossible. Otherwise remove every transition
producing into the trap and project away its coordinates. Trap closure ensures
retained transitions have no trap pre-arcs. Project every target constraint,
preserving bounds, equality flags, and constraint order (including constant rows).
Keep original place and transition order; replay lifted positives on the original.

Rust module `target_zero_trap`:
- `prepare(p, deadline, max_work) -> Result<Preparation>`.
- `Preparation::Marked { trap: Vec<usize> }` or `Preparation::Reduced(Prepared)`.
- Prepared public fields `problem`, `places`, `transitions`, `trap`.
- `Prepared::lift_witness(original, trace, deadline, max_work)` as relevance API.
- `Prepared::wrap_proof(inner, deadline, max_work) -> Result<Value>`.
- `verify_reduction(p, proof, deadline, max_work) -> Result<(Prepared, &Value)>`.
- `verify_marked(p, proof, deadline, max_work) -> Result<()>`.

Negative schemas (strict field sets; sorted unique trap indices):
- `{"kind":"target-zero-trap-v1","trap":[...],"inner":{...}}`
- `{"kind":"target-zero-trap-marked-v1","trap":[...]}`

Checkers independently validate forced-zero support, trap closure, and initial
emptiness/markedness. Maps are reconstructed, never trusted. The provided trap
need not be maximal. Reduction requires initial emptiness and an independently
checked inner negative proof. Marked proof requires at least one initial token
in the trap. Nested reduction checks share the existing deadline/depth bound.
Empty traps are harmless identity reductions, but do not prove unreachability.
No unaudited negative answer may bypass the wrapper.
