# Target-zero trap candidate review

The opt-in `--target-zero-trap` flag precedes existing relevance/portfolio search.
PNML capacity discovery remains in its existing position. Defaults, schedules,
mathematical arithmetic limits and frozen comparison binaries are unchanged.
This is an implementation of a standard trap argument, with no novelty claim.

A bound-zero same-sign equality, or a lower inequality with nonpositive
coefficients, forces every supported coordinate to zero. The greatest trap
inside these coordinates is obtained by removing input places of transitions
with no remaining trap output. Each removed place and incidence is processed
once. The final trap is checked independently of that worklist.

A marked trap cannot become empty under positive-weight ordinary Petri-net
semantics, including weighted reads and self-loops. Thus an initially marked
trap refutes the target. Starting empty, every target-reaching run avoids every
transition producing into the trap. Closure ensures retained transitions cannot
consume from it either. Projection preserves all other arc weights, initial
coordinates and target constraints (including constant rows). This gives an
exact reduction for target reachability, not a global reachable-state invariant.
Positive answers map transition indices and replay the original weighted net.
Negative answers require either the marked-trap certificate or a checked inner
proof under the explicit reduction wrapper. Uncertified exhaustion is Unknown.

Root reviewed Rust discovery/projection/replay, Python certificate reconstruction,
CLI integration and test scope. A separate reviewer found no soundness defect
in these components. Two review findings were addressed: the contract now states
that preparation limits fall back to original search while failed answer lifting
returns Unknown; direct Python proof dispatch now rejects `-O`, preventing
assertion-dependent legacy leaves from being bypassed inside a new wrapper.
The production original-input validator already rejected optimized Python.

Validation on final Rust sources: 390 tests passed, one pre-existing ignored;
15 new tests include 1,056 finite two-place/two-transition reachability comparisons
and greatest-trap checks, weighted arcs, draining chains, malformed certificates,
limits, original-index replay and EF/AG CLI polarity. Formatting and Clippy passed
(vendor warnings unchanged). Release build passed. Python checks: 64 integration
tests passed, then 19 runner/original-validation tests passed after adding the
per-method benchmark flag. The 14 new checker tests include a subprocess that
verifies `python -O` rejects a forged wrapped negative. Earlier agent optimized
mode test results predate this guard and are not validation of the final dispatcher.

Proof nesting shares existing deadline/depth limits. Arithmetic overflow, work
limits and timeouts return Unknown. These checks do not establish arbitrary-net
reachability completeness, performance gains or publication readiness.
