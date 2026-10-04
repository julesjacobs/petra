# Certified bounded token-flow cuts

The `bounded-token-cut` method adds certified finite place bounds to the existing per-place flow relaxation. This closes one specific weakness: a data cut can now cross an outgoing edge inside a strongly connected controller. It does not make the relaxation complete for reachability.

## Finite place bounds

A sparse rational potential has nonnegative weights `w[p]` and satisfies

```
w · post(t) <= w · pre(t)
```

for every original transition. Exact rational checking establishes that `w · m` never increases along a firing sequence. Consequently each positive coordinate supplies the global bound

```
U[p] = floor((w · initial) / w[p]).
```

`src/place_bounds.rs` discovers proposals with LP, checks them exactly, and reuses each verified potential for all its positive coordinates. Multiple potentials give the minimum supplied bound for each place. Failure to discover a potential is not evidence of unboundedness. Bounds use arbitrary-precision integers.

For an abstract edge `e`, let `n[e]` be its count, `y[e,p]` its source token moment, and `l[e,p]` its enabling lower bound. A certified global bound permits

```
l[e,p] n[e] <= y[e,p] <= U[p] n[e].
```

After substituting `f[e,p] = y[e,p] - l[e,p] n[e]`, residual flow has capacity `(U[p]-l[e,p]) n[e]`. If the lower bound exceeds the certified upper bound, the original transition is disabled. The initial implementation safely relaxes its upper bound to its lower bound, avoiding a negative capacity. Proving its count zero is a possible strengthening. Selected controller places retain their exact source marking bounds.

Unlike replacing infinity by a finite number for a particular max-flow computation, these capacities are justified for every concrete execution. A zero candidate count gives zero capacity on a genuinely bounded edge. An unbounded edge still has genuinely infinite capacity, even at candidate count zero.

Certificates (`bounded-token-cut-v1`) include the original place potentials, the control projection, flow-cut descriptors, and exact terminal Farkas proofs. The verifier reconstructs all rows from the original net and independently checks the potentials before using their bounds. The low-level `bounded_cut_row` and `separate_bounded_place` APIs assume their bounds are already certified; `verify_bounded_certificate` establishes that assumption.

## Strict strengthening on a strongly connected controller

The executable regression fixture in `tests/bounded_token_cut.rs` has four places `A,B,x,y`, initial marking `(1,0,2,0)`, and two transitions:

| Transition | Input | Output |
| --- | --- | --- |
| `a` | `A + 2y` | `B + 2y` |
| `b` | `B + x` | `A + y` |

The query is `B=1` and `y=1`. The abstract controller is the strongly connected cycle `A -> B -> A`. The concrete initial marking is deadlocked, so the query is unreachable.

The state equation forces `n[a]=2`, `n[b]=1`, with final `x=y=1`. The unbounded token-moment relaxation accepts this point. For example its data moments can be

```
y[a,y]=4, y[b,y]=3,
y[a,x]=2, y[b,x]=1.
```

The potential `x+y` is conserved and initially equals two, giving `y<=2`. Thus `y[b,y]<=2 n[b]=2`, which conflicts with the required moment three. Equivalently the subset cut for `{B}` is

```
final_y - 2 n[a] + 2 n[b] >= 0.
```

The candidate gives `1-4+2=-1`. The unbounded separator cannot use this subset because it crosses an unbounded outgoing edge. The bounded method discovers sufficient potentials and cuts automatically and emits a checked unreachability certificate through the CLI.

This example establishes strict expressive strengthening over the fixed unbounded moment relaxation. It is a designed diagnostic, not a performance benchmark or evidence of superiority to a competing solver.

## Verification performed

`cargo test --test bounded_token_cut` passes all five tests:

- The strongly connected example has an exactly checked feasible unbounded LP model and an exactly checked infeasible bounded LP, and the solver emits a valid certificate.
- Ten rational fixed-count points are checked against an independently constructed full moment LP with upper-bound rows: six exact feasible models and four exact Farkas refutations agree with separation.
- All mode-subset cuts preserve concrete walks through depth six in a variant with weighted reads, repeated control visits, and unguarded transition copies. The reachable query variant produces a replayed witness.
- Certificate checking rejects negative potential weights, omitted potentials, an added producer, and an increased initial marking that invalidates the recorded proof.
- A subprocess invokes the actual `bounded-token-cut` CLI and the returned certificate passes the Rust verifier.

The full moment LP in these tests is built from `token_flow::relaxation` plus explicit upper-bound rows; no min-cut construction is used to decide its feasibility. An independent Python checker in scripts/bounded_token_cut_checker.py additionally accepts the actual Rust-generated research/bounded-cycle-answer.json and research/g2-bounded-token-cut.json certificates; all45Python certificate tests pass. No performance conclusion is drawn from test execution while unrelated build work was active.

## Remaining limitations

The global bounds ignore relationships between places at individual edge occurrences. Separate upper bounds may permit incompatible source moments even when each per-place flow is feasible. Conditional bounds by controller mode, coupled moment inequalities, and support or integer refinements remain possible extensions. Candidate discovery and all algorithmic budgets remain incomplete: failure gives unknown. Novelty, broad benchmark gains, integration into the default portfolio, and held-out performance remain unverified.
