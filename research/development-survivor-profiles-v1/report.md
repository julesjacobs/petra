# Survivor stage diagnostics

Five original survivor branches ran through the frozen combined candidate with
VASS_PORTFOLIO_PROFILE=1, five seconds internal budget and seven seconds external
budget. All processes completed; audit.json checks pins and paired phase records.
These instrumented runs are excluded from benchmark coverage and timing claims.

Both DoubleExponent RC02 branches spend about 3 ms obtaining one integer model
and exploring 68 realization edges, then return no witness. RC07 branch 0 tries
three models, performs one support refinement and explores 138 edges in about
8 ms. The reduced BFS stage reaches its 200,000-state cap on all five branches.
The remaining search stages mostly exhaust their time budgets.

TokenRing's initial count stage is skipped by the existing size guard. Its causal
stage visits its 128-node limit, with 97 integer models and 97 support cuts. A
later count stage reports 87 support refinements. This is different from the
quick, support-feasible realization failures on DoubleExponent.

RC07 branch 1 again reports an unreachable certificate; the profile itself is
not counted as a checked benchmark result. The frozen survivor sweep independently
checked this branch six times while the whole property remained unknown.

The next diagnostic, ../count-obstructions-v1, independently exhausts the initial
integer models and identifies necessary execution-frontier constraints. The
reported phase times are observations from one local run, not stable estimates.
