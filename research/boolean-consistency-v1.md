# Boolean consistency development benchmarks

The 34-query corpus in `benchmarks/boolean-consistency-v1` complements the
368-query MCC stress set and the raw serializability queries. It isolates
combinatorial search difficulty in small ordinary Petri nets. It is synthetic
development data, not evidence about typical application performance or an
independent evaluation set.

## Selection fixed before measurement

`scripts/generate_boolean_nets.py` generates every case in this ladder:

- Random 3-CNF: 24, 48, 72, and 96 variables; clause/variable ratios 3.80,
  4.26, and 4.80, rounded to the nearest clause; two recorded seeds. Each
  clause uses three distinct variables. Duplicate clauses are rejected.
  No satisfiability filtering or planted assignment is used: 24 queries.
- Pigeonhole: 4, 6, 8, 10, and 12 holes; equally many pigeons and one extra
  pigeon at each size: 10 queries, paired positive and negative instances.

All original PNML/XML, canonical JSON, translated Tina inputs, DIMACS formulas,
parameters, and file hashes are retained. The manifest works with the existing
original-input benchmark harness. No preprocessing or decomposition occurs
in generation. A competing tool may perform its normal preprocessing within
its deadline. Source expectations are metadata and are not passed to solvers.

## Encoding and correctness

One control token passes through variable assignments and then clause checks.
At variable i, either assignment transition creates its true or false token.
Assignment tokens persist. Each clause has one transition per literal, which
reads the corresponding assignment token using an ordinary consume/produce
self-loop and advances the control token. The target is one token in the
final control place.

A satisfying assignment gives a firing sequence: choose its values, then
choose a true literal of each clause. Conversely, any sequence reaching the
target chooses exactly one value per variable and tests a true literal in
every clause. Thus target reachability is equivalent to satisfiability.
Every place is 1-safe. No fairness, capacities, inhibitor arcs, or arithmetic
overflow assumptions are needed. A successful sequence has exactly n+m
firings, so difficulty need not arise from a very long witness.

The pigeonhole formula requires every pigeon to occupy at least one hole and
forbids two pigeons from sharing a hole. Equal sizes admit the diagonal
placement; more pigeons than holes is impossible. Multiple holes per pigeon
are allowed by the formula and do not invalidate either argument.

Four generator tests pass, including exhaustive state-space/truth-table
agreement on 40 small random formulas, exhaustive positive/negative
pigeonhole instances, 1-safety checks during exploration, and PNML/XML
roundtripping. This validates the encoding on these cases; the preceding
argument explains the general construction.

## Measurement

The frozen plan is `research/boolean-consistency-v1-plan.json`. The first pilot
uses the existing frozen Rust `portfolio-local` and unrestricted VerifyPN,
five seconds per original-input query, one repetition, Linux CPU 8, a kernel
enforced 2 GiB limit, and instruction counters. Native answers additionally
undergo the existing separately bounded independent checker. Keep every
query in the denominator, including timeouts and checker failures. The pilot
does not measure the pending solver changes.

The completed pilot solves8/34with Rust and5/34with VerifyPN;25remain unresolved by both. See `research/harder-test-set-v2.md` and the complete preserved results.
Synthetic cases should remain a separate table from application benchmarks.
The reserved MCC evaluation families remain untouched.

## Source-formula diagnostic

`research/boolean-consistency-source-oracle.json` records a separate Z3 check
of all 24 random formulas: 10 SAT and 14 UNSAT. SAT assignments were evaluated
against every original clause; UNSAT answers have no separately checked proof.
Every Z3 check took under 5 ms in this untimed Mac diagnostic. This is evidence
that the source formulas are easy for a dedicated Boolean solver, even when
their Petri-net encodings are difficult for the tested reachability tools.
The useful distinction is representation and symbolic reasoning, not a claim
that these are intrinsically hard SAT competition instances. Source-oracle
answers are not substituted for any timed Petri-net result.
