# Linux hard-development comparison

The original complete matrix contains **276 rows over 69 properties**. Checked
Rust coverage was 48/69 for the focused portfolio and 49/69 for the symbolic
portfolio. VerifyPN reported 32/69 definitive answers and SMPT reported 9/69;
external answers were not independently certified.

| Method | Reachable | Unreachable | Unknown | Error | Definitive |
|---|---:|---:|---:|---:|---:|
| Rust focused | 46 | 2 | 21 | 0 | 48 |
| Rust symbolic | 47 | 2 | 13 | 7 | 49 |
| VerifyPN default | 30 | 2 | 37 | 0 | 32 |
| SMPT full portable | 1 | 8 | 60 | 0 | 9 |

| Development track | Properties | Rust focused | Rust symbolic | VerifyPN | SMPT |
|---|---:|---:|---:|---:|---:|
| FastForward random walks | 43 | 37 | 37 | 17 | 0 |
| MCC stress | 16 | 11 | 12 | 15 | 1 |
| Synthetic | 10 | 0 | 0 | 0 | 8 |

The original native union was 49/69; the union across all four methods was
**61/69**, leaving six FastForward properties and two larger pigeonhole queries
jointly unresolved. Native results were strongest on the selected FastForward
track; VerifyPN covered more selected MCC stress properties, and SMPT supplied
synthetic negative answers. This is evidence of complementary coverage on this
selection, not general solver superiority.

## Separate certificate qualification

All 97 original definitive native rows passed independent original-input
translation and witness/proof checks. The seven symbolic errors were saved
random-3SAT negative answers exceeding the original **1 MiB response limit**.
Those seven original measured rows remain errors.

A previously registered, explicitly posthoc policy selected **every** native
validation-failure row from the completed matrix, without selecting by expected
success. All seven saved answers independently qualified as unreachable under
60 seconds, 2 GiB, a 64 MiB response cap and 200 million DAG-checker work items.
The original policy used 60 seconds, 2 GiB, 1 MiB and 20 million work items.
Answer hashes match the saved benchmark artifacts; original results and solver
timings are unchanged, and no solver was rerun. All seven proofs passed
independent original-input translation and Python DAG CNF/RUP checking, with no
remaining qualification failures or verdict disagreements.

These **seven separately qualified negatives** bring the symbolic portfolio's
available checked evidence to 56/69 (49 original plus seven posthoc), but do not
replace the original 49/69 benchmark score. All seven properties already had
SMPT-reported negative answers, so the all-method union remains **61/69**.
Qualification ran on Linux after the timed solver run and took 9.69–43.36
seconds per answer. These separately measured checker times are excluded from
solver timing. The saved policy uses the word “local”; that does not mean the
qualification ran on the Mac.

## Conditions and limits

This was one 60-second repetition per method/property on Linux x86-64,
AMD Ryzen 9 7950X3D, with CPU affinity8, a 2 GiB systemd/cgroup memory limit,
zero outer grace and a 2,000,000-state native cap. All tools received original
PNML/XML; startup, parsing and their in-process preprocessing were timed.
Native validation was separately bounded and excluded from solver timing.
VerifyPN used unrestricted defaults; SMPT's full portable portfolio enabled its
configured reduction and WALK, state equation, BMC, induction, k-induction,
PDR coverability/reachability/saturated reachability, SMT and CP modes.

Startup load average was **64.64, 47.18, 41.50** on 32 logical CPUs. Affinity
is not exclusive isolation. Instruction counters and cgroup CPU/memory records
provide additional evidence but do not remove deadline censoring or shared-host
uncertainty. Outer timeout counts were 15/12/36/40 and memory-limit events
3/1/1/20 in table order; all outcomes remain in the denominator.

The 69 properties were selected from prior development outcomes within the
**620-property parent corpus**. Reserved families remain untouched. One
repetition on a busy host supports a development comparison, not a stable
performance or publication-readiness claim. This run uses an earlier frozen
native binary and does not evaluate the newer target-directed stubborn variant.

Evidence:

- [Complete measured rows](../results/linux-hard-development-v2/runs.jsonl),
  [environment and tool identities](../results/linux-hard-development-v2/environment.json),
  [analysis](linux-hard-development-v2-analysis.json), and
  [identity/resource/answer verification](linux-hard-development-v2-verification.json).
- [Registered uniform qualification policy](hard-v2-uniform-validation-plan.json),
  [qualification report](../results/hard-v2-uniform-validation-v1/report.json), and
  [all seven qualification rows](../results/hard-v2-uniform-validation-v1/runs.jsonl).

All **74 native FastForward positive rows** additionally passed independent
replay against original LoLA nets and formulas: 37 focused and 37 symbolic
witnesses, covering 37 distinct properties. There were no replay unknowns or
errors in the completed run. [Replay report](../results/linux-hard-development-v2-lola-replay/report.json)
and [all replay rows](../results/linux-hard-development-v2-lola-replay/runs.jsonl)
record every selected positive.

The strict replay preflight initially rejected the derived manifest's source
mapping paths: all 43 retained the original import-relative spelling and were
missing under the derived corpus directory. The frozen manifest was preserved.
An explicit `--allow-unrebased-source-mapping` option permits only an identical
relative spelling whose derived file is missing and whose original mapping
bytes match the pinned digest. Each of the 43 exceptions is recorded in replay
provenance; all other identity, input-path, ordered-branch and digest checks
remain strict. The initial preflight failure is preserved beside the successful
replay, and six wrapper regression tests passed. No solver was rerun.
