# Rust reachability portfolio results

**Final portfolio: 211/218 solved; SMPT: 210/218.** Three repetitions, two-second solver budget, zero conflicting definitive verdicts. Rust solves c5_disjunct_0 in all three runs; SMPT times out on it in all three.

Median backend wall-time speedup on 210 commonly solved queries is **19.34x**; excluding 83 syntactically false targets it is **18.93x** on 127 commonly solved queries. Other compiler workloads were active, so these are exploratory timings. They include startup and parsing, and exclude frontend generation and frontend proof validation.

| Engine | Reachable | Unreachable | Unknown | Runs per query |
|---|---:|---:|---:|---:|
| bfs | 14 | 16 | 188 | 1 |
| best-first | 3 | 16 | 199 | 1 |
| state-equation | 0 | 191 | 27 | 1 |
| integer-state-equation | 0 | 195 | 23 | 1 |
| marked-traps | 0 | 193 | 25 | 1 |
| support | 0 | 0 | 218 | 1 |
| klm-schemes | 4 | 16 | 198 | 1 |
| portfolio-old | 13 | 191 | 14 | 1 |
| portfolio | 14 | 197 | 7 | 3 |
| smpt | 13 | 197 | 8 | 3 |

External KReach (unverified adapted build), one run per query: 0 reported reachable, 157 reported unreachable, 61 timeouts/unknown, 0 errors. No reported verdict conflicts with the checked Rust results; no additional query is solved. This agreement does not establish correctness.

## What contributed

- Rational equality substitution fixes both previous elimination-limit gaps.
- Integer rounding cuts add four unreachability proofs beyond rational reasoning.
- Marked traps add e1_disjunct_0 and e7_disjunct_0.
- Standalone BFS finds c5_disjunct_0 at 35,500 states. This motivated a second BFS slot in the final portfolio.
- Path-scheme acceleration adds no unique solved SER query over BFS; it passes a separate 10,000-token repeated-word test.
- Support refinement adds no solved SER query in this corpus.

## Scope and algorithm status

The native Rust engines remain incomplete. `klm-schemes` is bounded exact repeated-word search, not full KLMST decomposition/refinement. The external Haskell KReach implementation is the Kosaraju/KLMST-family experiment and uses Z3 internally. Its adapted build failed direct-read-arc and multiple-control-state smoke tests. The benchmark uses a larger single-state pure-VAS encoding, with target conversion outside timing; its verdicts have no independent certificates. See [KReach findings](../research/kreach-build.md).

All 633 definitive native outputs in the repeated comparison passed independent Python checks: witnesses, integer cuts, marked traps or reconstruction of finite closure. 27 Rust tests, the artifact-dependent arithmetic-gap regression, Clippy, and 150 independent target-adapter differential cases pass.

The 218 queries were collected from 47 source benchmarks, with frontend timeouts and short-circuiting. This is not an exhaustive disjunct export or an end-to-end serializability result. No positive result relies on a feasible state equation, and bounded search failure remains unknown.

The all-method ablation used the initial portfolio schedule; the final comparison adds the second BFS slot. Standalone engines are unchanged. `portfolio-old` uses the original scheduling policy with the improved rational engine, while `results/comparison` preserves the original 202/218 implementation result.

## Reproduce

```sh
cargo test
cargo test --release --test arithmetic_gaps -- --ignored
cargo clippy --all-targets -- -D warnings
cargo build --release --locked
python3 scripts/test_kreach_adapter.py
python3 scripts/benchmark.py --seconds 2 --repeat 1 --methods bfs best-first state-equation integer-state-equation marked-traps support klm-schemes portfolio-old portfolio smpt --output results/new-ablation
python3 scripts/benchmark.py --seconds 2 --repeat 3 --methods portfolio smpt --output results/new-comparison
scripts/setup-kreach.sh
python3 scripts/benchmark.py --seconds 2 --repeat 1 --methods kreach --output results/new-kreach
```

Raw runs, per-query logs, certificates, hashes and environment information: [ablation](portfolio-ablation/REPORT.md), [repeated comparison](portfolio-comparison/REPORT.md), [KReach](kreach/REPORT.md).
