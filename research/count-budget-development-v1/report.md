# Count-budget development comparison

The remaining-state count cap preserved exactly the fixed-cap planner’s coverage:
93 reachable properties out of 192, with no gains or losses. The independently
checked RefineWMG gain is in the harder original-input cohort, outside this screen.

| Method | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Fixed cap 8192 | 93 | 0 | 99 |
| Remaining-state cap | 93 | 0 | 99 |
| Frozen SMT cycles | 69 | 0 | 123 |
| Frozen native walk portfolio | 101 | 85 | 6 |
| Frozen existing portfolio | 98 | 85 | 9 |

All 960 rows passed the artifact audit with zero warnings or answer disagreements.
Both count planners found the same 24 additional positives over the SMT prototype,
but neither added a positive beyond either native control. Both missed eight walk
positives: DoubleExponent-PT-003 RC13, TokenRing-PT-005 RC08/RC15, and
TokenRing-PT-015 RC08/RC10/RC13/RC14/RC15.

Each count mode attempted 272 branches with no expirations or sampled memory-limit
failures. Peak sampled RSS was 63,471,616 bytes for fixed cap and 65,077,248 bytes
for remaining-state cap. This is one shared-Mac development repeat, with one second
per property shared across canonical branches, sampled 2 GiB limits and separate
independent checks. It does not establish stable timing or general superiority.

Plan SHA256: `40655271b11a809126e02abe33c0c23d5361c027ca2911b8b4c4153b2d8ca749`.
Frozen sources and binaries: `results/solver-count-budget-development-v1`.
Raw evidence: `results/count-budget-development-v1`.
Audit and resource diagnostics: `audit.json` and `diagnostics.json` in this folder.

Next, evaluate a short remaining-state count stage inside the walk portfolio,
retaining its negative-proof methods. Standalone success does not establish that
portfolio preprocessing or time allocation preserves the gain.
