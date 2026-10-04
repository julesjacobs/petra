# Original-input Linux comparison

The complete 1,584-row run terminated with exit 0 and passed the artifact audit
with no audit issues or answer disagreements. It covers all 176 development
properties (175 exact ordered-branch representatives), nine configurations, one
repeat, a five-second property budget, CPU8 affinity, enforced2GiB memory, original
PNML/XML input, and separately bounded native answer checking.

| Method | Reachable | Unreachable | Solved / 176 |
|---|---:|---:|---:|
| Native walk portfolio | 87 | 45 | 132 |
| Native batched portfolio | 83 | 45 | 128 |
| Frozen native solver | 83 | 45 | 128 |
| VerifyPN default | 83 | 46 | 129 |
| SMPT full portable | 47 | 30 | 77 |
| SMPT compact portable | 47 | 30 | 77 |
| SMPT PDR | 19 | 7 | 26 |
| SMPT saturated PDR | 15 | 11 | 26 |
| SMPT official MCC portable configuration | 51 | 45 | 96 |

The walk portfolio adds four checked positive answers over the frozen solver and
loses none. All four are RERS17pb114 properties and are unresolved by every tested
competitor. Against VerifyPN it gains five properties and loses two, a net margin
of three. Against SMPT MCC it gains 36 and loses none on this screen. Stronger SMPT
configuration matters: MCC solves 19 more than full or compact at this budget.
These are observed coverage differences, not a general superiority or stable speed
claim. Native answers have saved independent-check evidence; competitor answers
remain tool-reported.

VerifyPN alone solves CloudReconfiguration-PT-311__RC06 and
RefineWMG-PT-100101__RC11. Forty-two properties remain unresolved by all nine
methods, concentrated in DNAwalker and RERS17pb114; one is an exact duplicate.
They form a reproducible source of harder development cases, but five-second
failure does not prove intrinsic difficulty. No holdout is consumed by this run.

Four audit warnings concern missing/partial perf counters on two interrupted SMPT
saturated-PDR runs. No counter values were imputed. Timeouts/nonzero exits and all
raw results are retained; they are not excluded from the denominator. CPU affinity
is not exclusive host isolation, and one repeat cannot establish stable timing.

Collection retained 6,060 files from a 4,331,803-byte archive, SHA256
86014ebcbe46887b0d9e753422143317c4510540a88b1a28810f54dd654ce04c.
The first import stopped before writing result files because local and remote
dispatch receipts had different formatting but identical JSON. Both are preserved;
remote bytes are under remote-receipts/dispatch.json and collection.json maps every
archive path to its imported path. The existing archive was imported without
retransferring. The failed collector/log were retained. See audit.json, summary.json,
plan.json and collection.json for identities, paired differences and qualifications.

This establishes a harder complete screen and modest improvement over the frozen
solver. It does not meet the goal's substantial-performance-advantage or coherent
research-contribution requirements.
