# Petra

Petra is an experimental Petri-net reachability solver written in Rust. It reads ordinary P/T nets in PNML and reachability or invariance properties in MCC XML. Build with `cargo build --release --locked`, then run `target/release/vass-reach --pnml model.pnml --xml properties.xml --property-id QUERY_ID --seconds 5 --max-states 2000000 --buffer-agglomeration`. See [setup and tests](publication/README.md) and the [full documentation](RESEARCH.md).

The default solver combines proofs and search under one property budget. It first tries to rule out the target using bounds on token totals and the state equation `m = m₀ + Cx`, where `C` records each transition's token changes and `x ≥ 0` counts firings, ignoring their order. A linear-programming solver proposes contradiction certificates, checked with exact rational arithmetic. Remaining cases use target-guided walks, structural reductions, and further search and proof methods. Firing sequences are replayed; invariance properties are checked by searching for counterexamples. Exhausting the budget returns `unknown`.

The [competitor comparison](research/competitive-linux-20261004/REPORT.md) used 368 development properties from 12 MCC families, five seconds per property, one logical CPU, and 2 GiB per invocation. The table averages the percentage solved over two Linux runs with an earlier Petra snapshot. The host was heavily loaded; these results do not establish general superiority. Failed runs count as unknown. Petra's answers were independently checked outside the solver budget; competitors' answers are tool-reported. The latest Petra reached [98.9% solved in both runs](research/verifypn-learning-20261004/full-v3/REPORT.md) in a separate experiment and has not been rerun against competitors. Inputs and raw results are in the [release archives](https://github.com/julesjacobs/petra/releases/tag/research-2026-10-04).

| Solver and configuration | Average solved |
|---|---:|
| Petra | 95.5% |
| VerifyPN 4.5.0 (unrestricted defaults) | 81.1% |
| SMPT (portable MCC configuration) | 60.2% |
| ITS-Tools (MCC configuration) | 73.5% |
