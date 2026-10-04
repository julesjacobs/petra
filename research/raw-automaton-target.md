# Exact serial targets without semilinear expansion

`ser --export-raw-automaton` exports `ser-raw-v2`: the original request-tracking
Petri net, completion places, response places, and a finite serial automaton.
An edge records its source and destination state and emits one response-place
token. The frontend constructs this automaton directly from complete serial
requests. Its initial state is the program's initial global state; every
global state is accepting. The generic backend also supports a subset of
accepting states.

For a completed Petri marking m, the target holds exactly when its response
vector is outside the automaton's Parikh image. Order in the automaton matters
for choosing a path; only the path's response multiplicities are compared with
m. This is the same serial-language condition previously represented as a
union of linear sets. Export performs no Kleene expansion, complement,
reachability-query decomposition, or Petri-net simplification. Construction
of the network system and the serial automaton remains charged to export.

## Rust membership

Membership explores pairs `(automaton state, residual response vector)` from
the initial state and the marking's response vector. An edge is available
only when its label has a positive residual; following it subtracts one from
that coordinate. An accepting state with zero residual establishes membership.
Exhausting the finite reachable pair graph establishes nonmembership.
Memoization merges identical pairs. Each edge consumes a token, so a concrete
fixed vector always defines a finite search. The product can still be very
large: work/deadline exhaustion propagates as unknown, never nonmembership.

Every solver-positive trace is replayed on the original Petri net and its
final marking checked again. The existing component-invariant discovery and
verification explicitly reject v2 targets; there is no v2 negative proof yet.
The v1 format and its required semilinear field remain supported.

## Independent checking

`scripts/raw_automaton_check.py` decides fixed-vector membership using Z3
integer edge counts rather than residual-vector search. It requires:

- nonnegative integral multiplicities with the requested label totals;
- Euler flow balances from the initial state to one accepting endpoint;
- positive-count support reachable from the initial state, certified by a
  strictly decreasing predecessor rank for each used noninitial vertex.

Necessity follows from a path and a spanning tree of its support. Conversely,
the balance conditions and rooted support permit an Euler trail through all
edge copies, with exactly the specified label totals and an accepting endpoint.
A disconnected circulation cannot satisfy the rank conditions. Thus Z3 UNSAT
proves nonmembership for the proposed witness. Z3 unknown or deadline expiry
rejects the proposed answer as unknown. This checker is independent of Rust's
search; Z3's UNSAT result is trusted, as in the previous component checker.

## Linear guidance on either representation

Existing raw-potential search uses sufficient forbidden linear inequalities.
For a response form y (one coordinate or a coordinate difference), the
automaton implementation weights each edge by the y-value of its label and
computes maximum path weights by Bellman–Ford relaxation. A reachable positive
cycle causes that candidate to be skipped. Otherwise the maximum accepting
path value b bounds every serial vector, so `y*m >= b+1` is a sufficient
nonseriality goal. A positive cycle that cannot reach an accepting state is
also skipped conservatively; this loses guidance but cannot invent a witness.

The guided solver still checks the complete original target. Finite linear
bounds are guidance, not an exact representation of the complement. No
publication novelty is claimed for automaton Parikh membership, connected
integer flow, or this longest-path construction.

## Validation and benchmark evidence

Four frontend tests include bounded agreement with the existing v1 semilinear
image, empty history and immediate responses. A smoke test preserves exact v1
output bytes and deterministic repeated v2 bytes. Rust checks 1,024 membership
queries against explicit word enumeration over 64 small automata. Python
checks its flow encoding against word enumeration, including disconnected
cycles and malformed inputs. Tests also cover exhausted budgets, missing v1
targets, and finite linear bounds on balanced cycles.

The previously frozen twelve diverse SER sources all export in the new format:
8.90 seconds total locally, versus ten component-limit failures and two memory
limits with v1. The largest JSON is about 42 MB. Export timings are exploratory
Mac measurements; the original failures and all sources remain preserved.
`benchmarks/raw-diverse-automaton-v1/collection.json` records every command,
source hash, output hash, and resource result.

The corrected initial full pilot, `results/raw-diverse-automaton-v2`, verifies
four positives with raw BFS and five with raw search out of all twelve sources;
seven remain unresolved by both. Every accepted positive has independent
original replay and connected-flow nonmembership checking. These are Mac
development results at a five-second input-inclusive deadline with sampled
2 GiB accounting. Source-level expectations remain separate from solver results.
The first pilot is retained: its parent protocol did not recognize the new
checker label and therefore rejected otherwise checked positives. The corrected
pilot was rerun in full rather than rewriting those rows.

The separate potential-guidance experiment uses
`results/solver-automaton-potentials-v1` and
`results/raw-diverse-automaton-potentials-v1`. Its complete 48-row matrix verifies six of twelve programs in both repetitions,
versus five for raw search, gaining optimistic_v9_aba and losing none. The six
remaining programs are unresolved; their source-level serializability arguments
are not checked negative reachability answers. See
`research/raw-diverse-automaton-potentials-v1-analysis.json`.

Reproduction: `scripts/setup-raw-automaton.sh` applies the original raw export
patch followed by the preserved incremental automaton patch. The old and new
frontend binaries/sources are frozen in `results/frontend-before-automaton-v1`
and `results/frontend-automaton-v1`.
