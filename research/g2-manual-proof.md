# Manual proof: g2_disjunct_1 is unreachable

Instance: `results/portfolio-larger-budget/g2_disjunct_1.json`, exported from `examples/ser/g2.ser` in the serializability artifact. This is one backend target disjunct, not a proof of the entire source benchmark.

The target requires no pending requests/responses, at least one completed transfer returning 350, and strictly more completed transfers returning 300 than 350.

Let C300 count both pending and delivered transfer results of 300 (places 18+19), and C350 count both pending and delivered transfer results of 350 (places 22+23). Counting pending results prevents response-delivery order from breaking the invariant. Let q be the unique global control token. All original transitions preserve exactly one global token.

Partition the global states into three regions:

| Region | States (A,B), with X=1 unless uninitialized |
|---|---|
| Pre | uninitialized; (100,50); (50,100) |
| Low | (200,100); (150,150); (100,150); (200,150); (50,150) |
| High | (100,200); (50,200); (200,200); (150,200) |

The following disjunction is inductive:

1. q is in Pre and C300=C350=0; or
2. q is in Low and C350=0; or
3. q is in High and C300-C350+[q=(150,200)] <= 0.

Initialization is immediate. Low and High are individually closed. Pre can enter either; it enters High only at (100,200), with both counters zero.

Within High, a transfer returning 350 moves (200,200) to (150,200). A transfer returning 300 moves (150,200) to (100,200). The latter is the only way to produce a 300 in High, and the former is the only way to enter (150,200). Other transitions do not increase the displayed potential. In particular, interest at (150,200) leaves that state unchanged; its returned value does not count as a transfer response.

Thus the target's positive C350 excludes Pre and Low. In High, C300<=C350. At the target all pending-result places are empty, so these counts equal completed responses. This contradicts R300-R350>=1.

## Independent mechanical check

`python3 scripts/check_g2_manual.py` checks the one-token control invariant, the three-region inductive conditions against all original arcs (202 enabled control/transition cases), and the target contradiction using Python integer arithmetic. It uses no SMT solver and does not invoke any Rust reachability engine. The partition is supplied manually, not discovered by the checker.

Historical status: the old automatic portfolio reported unknown on this query. On 2026-09-27 the generic `token-moment` engine automatically refuted it using a discovered one-token controller and 12 exact terminal certificates, independently verified in Python. See `research/g2-token-moment.json` and `research/token-moment.md`. This establishes an automatic proof of this query; an integrated 218/218 timed portfolio run has not yet been measured.
