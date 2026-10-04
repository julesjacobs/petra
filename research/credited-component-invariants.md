# Credited component invariants

The raw SER query asks whether a completed marking has a response vector outside
the supplied serial language, a finite union of linear sets. This proof search
tries to show that every completed marking stays inside that language. It is
incomplete: failure to construct an invariant means unknown.

Let R be the response places and Z the completion-zero places. A credit map W
keeps every response coordinate unchanged and adds nonnegative weighted counts
from selected places in Z. Thus Wm equals the actual response vector whenever
m[Z] = 0. Credits account for responses that have been determined but have not
yet been emitted. Their interpretation is only a discovery heuristic; checking
requires the algebraic conditions below and does not trust program names.

An invariant node consists of an exact marking q on a selected set of controller
places and one original serial component b + B N^h. Its meaning is the set of
original markings m with controller projection q and Wm in that component.
Unselected counters are unrestricted. A finite set of nodes describes the
invariant as a union of these sets.

For every node and every original transition whose controller preset is enabled,
the certificate supplies a destination node with the exact controller successor.
Writing a for the credited transition effect, it also supplies nonnegative integer
coefficients v and H satisfying:

```
b + a = b' + B'v
B     = B'H
```

The certificate stores each column sparsely. These equalities show that a source
valuation b + Bz maps to b' + B'(v + Hz) for every z in N^h. A transition with
both zero controller incidence and zero credited effect preserves every piece
and needs no explicit edge. The checker derives this exception from original
arcs, including their weights.

The initial marking must belong to the initial node, with explicit period
coefficients. Induction on an original firing sequence proves invariant membership:
an enabled original transition is enabled in its controller projection, and its
checked affine map preserves membership. At completion all credits vanish.
Every node then gives membership in an original serial component, contradicting
the target's required nonmembership. This proves unreachability of the raw query.

The checker needs no separate boundedness theorem for the controller. Finite
closure of the submitted node set is checked directly. Discovery selects places that are not response coordinates, credit columns, or
outputs of transitions with an empty preset. This keeps transient guards as well
as global state, without solving an auxiliary conservation problem. Syntactically
enabled but unreachable transitions can violate a global conservation equation
while the projected reachable markings still have finite closure. An unbounded
projection causes bounded discovery to return unknown.

Discovery matches original components using exact natural-monoid decompositions
and caches transfer maps by source component and credited effect. It currently
chooses the first covering component. This choice can fail even when a different
assignment, a union of destination pieces, or a synthesized invariant would work.
Resource limits and coefficient representation limits likewise return unknown.

The Rust checker and separate Python checker validate the original query and the
complete certificate. Neither uses the positive-only source/sink reduction.
Independent acceptance is required by the raw benchmark harness. Correctness
tests and successful individual certificates do not establish completeness,
novelty, publication readiness, or a performance advantage over other solvers.
