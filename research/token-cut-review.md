# Independent token-cut audit

Reviewed `src/token_cut.rs`, `src/flow.rs`, `src/control.rs`, the
`rational_model` addition in `src/linear.rs`, and the reference
`src/token_flow.rs`. This was a read-only reasoning review; no build, test,
or benchmark was run during the live benchmark.

No soundness blocker was found in the reviewed implementation.

## Derivation

An original execution induces one control path: selected places initially
contain exactly one token, every transition conserves their total, and
transitions consuming more than one selected token cannot fire. Stuttering
transitions are represented separately at every reachable control mode.
The constructor's graph search covers every concretely reachable mode,
including modes reachable only through transitions whose data guards are
ignored. Those extra modes weaken the relaxation safely.

For each graph edge e, let x_e count its occurrences. For a place i, let
y_e sum its markings immediately before those occurrences, and let delta_e
be its transition effect on that place. The balance at mode q is

    out(y,q) - in(y,q) = initial_i*[q=initial]
                            - final_i*[q=terminal]
                            + sum_{e entering q} delta_e*x_e.

Every execution satisfies the master's final-marking state equation,
control-path incidence, final one-hot control values, and target rows.
For data places y_e >= pre_i(e)*x_e. For selected control places
y_e = [source(e) occupies i]*x_e exactly. Read arcs and weighted arcs are
therefore handled with their enabling multiplicities, not merely effects.

Writing z_e=y_e-L_e*x_e gives nonnegative flow with demand

    d_q = initial_i*[q=initial] - final_i*[q=terminal]
            - sum_{e leaving q} L_e*x_e
            + sum_{e entering q} (L_e+delta_e)*x_e,

and capacity (U_e-L_e)*x_e when U_e is finite. For any set S,
sum_{q in S} d_q <= sum_{e leaving S} capacity_e. Rearranging gives
exactly `cut_row`:

    final_i*[terminal in S]
      - sum_{internal e} delta_e*x_e
      - sum_{entering e} (L_e+delta_e)*x_e
      + sum_{leaving e} U_e*x_e
        >= initial_i*[initial in S].

The outgoing edges must all have genuinely finite U_e. The implementation
rejects other symbolic cuts. This inequality holds for every original
execution, regardless of which candidate or terminal first exposed S.
Regenerating its final-marking coefficient makes caching across terminals
sound.

## Arithmetic and acceptance

- Rational proposals are reconstructed as nonnegative exact rationals and
  every original row is checked before separation. Independent rounding
  can miss a model, but cannot introduce an accepted invalid model.
- LCM scaling multiplies the demands and finite capacities uniformly.
  The bit limit returns unknown; it is absent from the trusted proof.
- An unbounded capacity remains unbounded even when x_e=0. The flow
  routine's supply+1 replacement is only numerical work on an exact
  integer instance. It exceeds every deficient cut capacity, and a
  returned cut is rechecked against original capacities. No replacement
  value enters `cut_row` or a certificate.
- Edmonds–Karp residual updates, reverse arcs, self-loops, demand signs,
  supersource visitation, and the final obstruction check are consistent.
- All terminal modes must have independently checked Farkas proofs.
  Bounded attempts, missing models, failed separations, or failed
  realizations yield unknown. The 8192-count cap only limits witness
  search; it does not enter negative reasoning.
- Summing edge counts by original transition loses control ordering,
  but positive acceptance reconstructs an original-net execution and
  replays it exactly, including the target. Thus this aggregation is safe.

## Important limit on strength

For a data place every current upper bound is infinity. Consequently a
valid data cut must be successor-closed in the entire controller graph.
In a strongly connected controller its only choices are the empty and
full mode sets, and the full-set inequality follows from the state
equation. Fixed control moments add no data ordering constraint.
Equivalently, any zero-total residual demand is routable on a strongly
connected graph with unbounded capacities. This relaxation therefore
cannot improve the state equation on such a controller except through
fixing the terminal control marking. Its useful phase information comes
from irreversible control progress.

Independently certified finite bounds on other places, or a richer
certified control partition, would extend the method to this important
class. This observation is mathematical analysis, not a measured result
or a novelty claim.

## Engineering follow-ups

The cached-cut insertion silently skips a `cut_row` error while retaining
the corresponding cut in the certificate list. For the current immutable
graph and validated generated cuts that error cannot depend on the
terminal, so this is not presently a soundness flaw; final verification
also rejects a mismatch. Prefer treating it as an explicit failure to
keep row numbering robust against future changes.

LCM scaling currently repeats over all values for every separated place.
Compute it once per master candidate if profiling warrants it. Master
construction and final verification lack deadline checks, so the outer
process deadline remains necessary for strict benchmark budgets.

Useful regression checks include enumerated concrete paths satisfying
all finite cuts, fractional candidates, zero-count unbounded arcs, and
certificate replay after changing the terminal. The concurrently added
tests were located but not executed as part of this audit.
