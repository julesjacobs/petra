# Double-lock gap: target-zero trap reduction

**Recommendation:** try a checked **target-zero trap reduction** before the
existing relevance/search portfolio. A static support calculation removes
**696/1,833 transitions (38%)** and **56/184 places (30%)** on this query.
This is a concrete preprocessing opportunity, not a demonstrated speedup or a
new reachability result. No solver/build/remote operation was run for this analysis.

## Verified model and diagnostic facts

Query: `ff_random_walk_double_lock_p2_vs_satabs_2_multi_100_0_c52c1204`.
Canonical SHA256:
`cd91aab47855d7447e827c9e8d64923bb8ade326a7262227579b67eb6814481b`.
Original source names were recovered from the checked source mapping; all proposed
rules depend on incidence and target constraints, not those names.

- 184 places: 129 `s` places and 55 `l` places; all arc weights are one.
- Initial marking: `s0=1,l0=1`. The 194 constraints specify all 184 coordinates
  exactly, with 174 zero coordinates and ten positive coordinates.
- Positive target: `s81=1`; local counts `l6=3,l5=7,l4=1,l3=2,l9=1,l30=1,
  l28=1,l41=1,l31=1` (18 local tokens).
- 1,736 transitions consume/produce one shared and one local token; 96 consume
  one shared/one local and produce one shared/two local tokens. One unconditional
  source transition produces `l0`. Thus shared-token mass stays one, total local
  mass never decreases, and the net is unbounded through the source transition.
- Every successful path increases local mass exactly 17 times and never exceeds
  18 local tokens. This is a goal-path fact, not a global reachable-state bound.
- 32 places are isolated and initially/target zero. Six produced-but-unread
  places (`s128,l40,l27,l54,l50,l53`) are also target zero. Directly entering these
  six places already makes the target impossible; 160 transitions produce one.

The completed local 30-second diagnostic, prepared by the parent agent, attributes
about 17.64 seconds to relaxed search (309,215/355,402 reported states) and about
4.2 seconds to guided search (1.51/1.52 million states). Parsing takes under 8 ms.
Both portfolios return unknown. These observations support prioritizing search
space reduction over parsing work. They do not show which visited states entered
the forbidden region. The current 300-second VerifyPN positive is parent-reported;
its witness has not been independently inspected here.

## Concrete target-zero trap

Start with every place forced to zero at the target. Repeatedly remove a place
from this set when a transition consumes it but produces no token into the set.
The remaining set F is a trap: every transition consuming F also produces F.
Equivalently, start from the positive target support, traverse transitions
backwards when all original post-places are available, and add their pre-places.
This is Boolean support propagation, not marking-space reachability search.

On this query the fixed point has **56 places**: 32 isolated places plus these
24 incident places:

`l52,l26,l38,s128,l47,l36,l40,l33,l27,l54,l50,l32,l37,l34,l45,l39,l48,l44,
l46,l53,l42,l49,l35,l43`.

I checked the trap condition against every original transition, and checked that
both initial and target markings are zero on F. Once any token enters F, some
F token must persist, so no target-reaching execution can use a transition that
produces into F. Removing these transitions and F leaves **128 places (96 shared,
32 local) and 1,137 transitions**: 1,072 conserve local mass and 65 increase it.
No target-reaching trace is intentionally lost by this reduction; implementation
still needs an independent certificate check and original-net witness replay.

## Why existing preprocessing misses this

`relevance::prepare` starts from all target-supported coordinates. Here every
place is target-supported and every transition changes one, so it retains the
whole net. `relaxed::Graph::new` has the same all-supported seeding limitation.

`reduced::prepare` recognizes special disposable source/private-completion
patterns. `l0` starts marked, so its source is not disposable under that rule;
no place has exactly one consuming transition. The target-zero trap is a different
structural condition and does not require such private incidence.

`structural.rs` already checks **initially marked** traps to strengthen arithmetic
refutations. F is initially empty; the useful fact is that the target also
requires it empty. Reuse the incidence condition but distinguish its purpose and
certificate from the existing marked-trap proof kind.

The symbolic phase rejected controller discovery in the local diagnostic. There
is nevertheless a statically valid one-token shared projection: its initial
abstract component has 97 modes and 1,929 explicit edges after source stutters,
exceeding the 1,833-edge limit passed by `dag_solve`. This is one plausible cause
of that generic rejection, not a verified explanation of the chosen LP projection.
The projection also has cycles, so merely increasing the edge limit would not
make the existing acyclic-controller SAT method applicable.

## Bounded next step

Implement only the target-zero trap preprocessing and its checker. Seed it with
coordinates independently proved zero by each target conjunction; if uncertain,
leave the coordinate out. Check the trap incidence condition on original weighted
arcs, preserve transition IDs, and replay any returned positive witness on the
original input. A negative answer from a reduced instance needs explicit reduction
proof lifting. Apply the same rule across application queries, including exact
zero-heavy FastForward targets, and measure removed structure plus end-to-end
coverage on the preregistered application screen. Do not tune the rule to this
model's names or reported answer.

Expected benefit remains uncertain: excluding irreversible dead regions is sound,
but we have not measured how often the existing searches enter them or whether
the remaining 1,137-transition net is easy. No solver implementation was changed.
