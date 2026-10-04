# Native scheme search development screen

All 960 rows pass the saved-artifact audit, with zero disagreements or validation
failures. Full 192-property coverage at one second per property:

| Configuration | Reachable | Unreachable | Unknown |
|---|---:|---:|---:|
| Native singleton schemes | 61 | 0 | 131 |
| Native cycle schemes | 60 | 0 | 132 |
| Frozen SMT cycle schemes | 69 | 0 | 123 |
| Frozen walk portfolio | 101 | 85 | 6 |
| Earlier frozen portfolio | 98 | 85 | 9 |

All methods cover the 47 initially satisfied properties. Native noninitial
positives are 14 and 13. Native cycles gains nothing over singleton schemes and
loses SharedMemory-PT-000005__RC13. It gains nothing over SMT or either native
control. Controls and SMT reproduce the preceding screen's coverage.

## Diagnosis

Completed native-singleton branches report 58,068 attempted schemes and 51,267
prefix refutations; native cycles reports 60,155 and 53,353 respectively. Native
singleton has one branch without final statistics. Outer deadline expiration
occurs on three singleton and one cycle branches; no memory-limit failures.

Of unresolved branches with statistics, 81 singleton and 113 cycle branches never
leave the initial word layer. This follows from the frozen breadth-first ordering:
with schemes <= vocabulary size, every attempted scheme has one word. Cycle
root-only branches spend 27,313 attempts on 25,656 impossible prefixes. A word's
exact initial hurdle can reject these before either integer query. Enabled root
words also admit count one, so their target-free prefix query is redundant.

The next candidate therefore checks exact root guards before arithmetic, records
those checks/refutations separately, and reserves the arithmetic-attempt budget
for initially enabled words. It preserves all executable schemes. This is a
measured search-cost issue, not evidence for a novel algorithm or an advantage.
The new implementation and tests are separate from this frozen v2 snapshot.

Evidence: audit.json, diagnostics.json, root-diagnosis.json, raw results under
results/native-scheme-development-v2, and frozen solver-native-scheme-development-v2.
The initial failed v1 smoke and snapshot remain preserved. One shared-Mac repeat,
canonical inputs, sampled2GiB memory, and separate checking do not establish stable
speed or held-out generalization. Phase totals omit killed branches and cannot be
interpreted as complete execution profiles. The default portfolio is unchanged.
