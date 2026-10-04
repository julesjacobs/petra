# Stubborn reduction diagnostics

All 32 planned rows completed: the original 13 selected properties plus three
screen gain/loss properties, each with focused and stubborn portfolios. Original
PNML/XML inputs, five-second internal budgets, seven-second diagnostic outer cap,
2 GiB, two million states, and separate stderr profiles. Every input hash remained
unchanged. All ten definitive answers passed independent original-input checking;
no validator failures or non-JSON stderr lines were recorded.

The baseline solved six properties and the reduction four. This outcome-selected
single diagnostic pass is not a repeat of the strict screen: the extra outer
grace permits final profiles and answers. Its timings must not replace screen
measurements.

Both configurations emitted 18 helpful-attempt and 15 unrestricted-fallback
profiles across branches. The reduction's fallback profiles report 36,627 expanded
nodes: 9,720 reductions, 19,061 visible full expansions, 4,407 periodic full
expansions, 3,409 previously-seen full expansions, 20 all-enabled and six closure
limit fallbacks. Four expansions had no completed selection before interruption.
Thus reduction activates, but visibility accounts for about 52% of expansions.

Baseline/reduction fallback totals were 1,827,373/1,388,125 processed firings and
1,762,735/1,329,058 inserted successors. These aggregate fixed-budget counts mix
search trajectories and solved outcomes; they do not establish a throughput or
state-space improvement on identical explored work.

All three selected FastForward cases had zero reductions. The apparent screen
gain on pthread5 multi60 did not repeat: baseline solved and reduction was unknown.
The FunctionPointer3 multi25 screen loss solved in both diagnostics. DLC8bRC00,
another screen loss, solved in both helpful-only phases before reduction. These
observations prevent attributing every coverage difference to actual pruning.
They do not erase the original gain or losses.

The complete machine-readable results and profiles are in
`results/stubborn-diagnostic-v1`; the parsed report is
`research/stubborn-diagnostic-v1-analysis.json`. The frozen-v1 full 624-row repeat
comparison remains registered and unlaunched. No stable improvement is claimed.
The target-directed alternative is now justified as an implementation experiment
by the independently reviewed proof and observed visibility/freshness fallbacks;
its performance remains unknown.
