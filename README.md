# Petra

Petra is an experimental Petri-net reachability solver written in Rust. It reads ordinary P/T nets in PNML and reachability or invariance properties in MCC XML. It combines invariant proofs, structural reductions and witness search, returning a firing sequence, an unreachability certificate, or `unknown` when its limits are reached.

Build with `cargo build --release --locked`. Run `target/release/vass-reach --pnml model.pnml --xml properties.xml --property-id QUERY_ID --seconds 5 --max-states 2000000 --buffer-agglomeration`. See [setup and tests](publication/README.md) or the [full documentation](RESEARCH.md) for other input formats and solver methods.

On the 368-property development set, Petra solved 364 properties in each of two five-second runs, up from 363 in the previous version, with no losses. All definitive answers were checked independently. These runs used a busy host; see the [research record](research/verifypn-learning-20261004/README.md) for the results and limitations. Full benchmark inputs, raw results and frozen experiment snapshots are included in the repository’s [release archives](https://github.com/julesjacobs/petra/releases/tag/research-2026-10-04).
