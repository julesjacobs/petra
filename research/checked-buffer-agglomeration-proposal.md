# Checked buffer agglomeration proposal

The opt-in implementation and independent checker are now present; see
buffer-agglomeration-contract.md and buffer-agglomeration-integration-status.md.
Performance has not yet been measured. The original proposal follows. Motivated by the original NoC3x3-PT-8B RC12 gap:
VerifyPN default reports199places/392transitions after reduction, whereas its
trace mode retains506/876 and timed out at60s. Both started9140/14577. These
observations do not isolate one rule. VerifyPN's source disables rulesR/S when
trace reconstruction is enabled. The existing Rust eager completion requires
unread output places; static inspection finds80 such initial candidates versus
6741 for a broader single-consumer condition. Static eligibility is not proof
that a whole reduction succeeds or improves time.

A coherent extension is ordinary-net buffer agglomeration with checked macro
trace recipes. It must preserve existential reachability of the full target
conjunction, including exact equalities, rather than only coverability. This is
classical structural-reduction territory; no novelty claim.

## Minimal uniform-weight rule

Choose a place p initially empty and absent from every target row. Let P be all
transitions producing into p, and C all transitions consuming from p. Require
both sets nonempty and disjoint, and require every incident arc to have the same
positive weight a. Accept either of the following sufficient conditions:

- Eager consumers: every c in C has pre-set exactly {(p,a)}, and every place in
  any c's post-set is absent from every target row.
- Delayed producers: every f in P has post-set exactly {(p,a)}, and every place
  in any f's pre-set is absent from every target row.

Replace all P and C by one macro transition for each ordered pair (f,c), remove
p, and retain other transitions. All incident weights match, so one producer
funds exactly one consumer. The macro recipe is f then c.

For eager consumers, macro pre=f.pre; macro post=(f.post without p)+c.post.
For delayed producers, macro pre=f.pre+(c.pre without p); macro post=c.post.
Combine duplicate remaining-place arcs by exact checked addition. Original
weighted self-loops on other places are preserved. Disjointness excludes a p
self-loop. If both orientations hold, fix one deterministic choice. Reject
nonuniform weights in the initial implementation rather than assuming units.
Reject growth beyond a preregistered transition/arc/work limit before mutation;
retain the original problem on preparation failure. Repeated application must
recompute incidence or maintain it soundly, and reach a fixed point within
explicit limits. Initial tokens and weighted batch variants are later work.

## Proof obligations

Each reduced macro has an exact original expansion f;c, preserving its guard
and update. Thus every reduced witness lifts. For the converse, match each
consumed p-packet to an earlier producer. In the eager orientation, commute its
consumer left to directly follow its producer: it consumes no other place and
only adds tokens elsewhere, so intervening original firings remain enabled.
Move any unmatched producers' consumers to the end using arbitrary available
consumer choices; these final firings change no target coordinate. Then commute
these firings to make adjacent pairs. In the delayed orientation, commute each
matched producer right to directly precede its consumer: it only produces p,
so postponement leaves additional tokens available to intervening firings and
cannot remove their required p-packet. Delete unmatched producers at the end;
their consumed coordinates are unqueried. In both orientations the final target
truth is preserved. Formalize the packet matching and commutation argument,
including producer/consumer dependencies through other places, before trusting
negative certificates. Test adversarial small cyclic nets, weighted self-loops,
shared inputs/outputs, and targets on forbidden coordinates.

Use a DAG of macro recipes with original transition leaves instead of repeatedly
flattening vectors during reduction. Bound DAG construction and witness
expansion/replay separately. Positive answers require original-input replay;
resource exhaustion returns Unknown. Negative answers require an independently
reconstructed sequence of valid agglomeration steps and a checked inner proof
on the final net. A certificate must not trust arbitrary replacement arcs,
renumberings, initial markings, or recipes. Keep stable identifiers during
steps, project disabled places only at the end, and reconstruct identical maps
in Rust and Python. Existing depth/deadline limits apply to outer proof nesting.
No unchecked reduced exhaustion may become an original negative answer.

The core rewrite should be opt-in, independently tested, frozen and evaluated
on the full existing development denominator and new application cases. Do not
retune or promote solely on NoC3x3. First implement/prove the uniform rule and
measure its net sizes; broader rules require separate contracts and evidence.
