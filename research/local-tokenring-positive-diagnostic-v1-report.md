# TokenRing direct-search diagnostic

All twelve registered rows completed: three selected positive gaps, four frozen
native configurations. None produced a definitive answer within the strict
five-second outer deadline. The artifact reconciliation passed; the full
nine-query competitor-only parent remains in `application-positive-gaps-v1.json`.
No new competitor run was performed.

Bypassing portfolio preparation did not recover these cases. Ten outputs contain
complete Unknown answers, two portfolio outputs are incomplete. The ten complete
answers report 0.030–0.138 seconds of parsing and approximately the remainder in
solving. Direct engines report thousands of states per branch (4,179–23,298), so
these runs do reach substantial search. Reported states are method-specific;
they are not directly comparable to competitor expanded-state counters. This
does not isolate heuristic cost, enabledness work, or search ordering.

Separate profiling of the three portfolio calls shows buffer agglomeration
inapplicable and brief (about 4–14ms). Causal solving consumes about 0.5s in each
first branch; later positive and negative stages run. The last quotient phase
has no observed end before the outer deadline and remains censored. Profile
measurements do not replace the unprofiled run. The evidence weakens the
hypothesis that parsing or portfolio-only preparation explains all nine gaps;
search guidance, query simplification and a lightweight walk remain candidates.

The SMPT WALK wins and VerifyPN searches in saved Linux logs motivate a fixed-seed
walk/restart experiment with original-net replay. That is a proposed solver
improvement, not an implemented or measured result. These queries are useful
solver-specific regression tests; other tools already solve them quickly.

Evidence: `local-tokenring-positive-diagnostic-v1-plan.json`,
`local-tokenring-positive-diagnostic-v1-verification.json`,
`results/local-tokenring-positive-diagnostic-v1`, and
`results/local-tokenring-positive-profile-v1`. Sessions 30511 and 87939 both
returned exit 0. No other local solver/build job overlapped these diagnostics;
Linux qualification was left undisturbed. Local timings are not compared
numerically with Linux timings.
