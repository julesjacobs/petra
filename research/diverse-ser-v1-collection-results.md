# Diverse SER collection results

All twelve sources in `benchmarks/diverse-ser-programs-v1` were attempted with
the existing frozen SER frontend, a 60-second wall limit, a sampled 2 GiB
process-tree RSS limit, and a sampled 1 GiB artifact limit. Collection is
separate from reachability timing. Every source parsed successfully.

| Family | Sources | Semilinear component panic | Memory limit | Valid queries |
|---|---:|---:|---:|---:|
| Ring write skew | 6 | 6 | 0 | 0 |
| Optimistic ABA validation | 6 | 4 | 2 | 0 |

The panic is the explicit `components.len() > 30` guard in
`vendor/SerializabilityChecker/src/semilinear.rs`, before subset enumeration
in Kleene star. The two largest ABA cases instead hit the sampled memory
limit. None reached query validation or solver execution. This establishes
an exporter limitation, not harder reachability performance and not a solver
failure. These sources remain prospective benchmarks until export succeeds.

`benchmarks/raw-diverse-v1/collection.json` preserves commands, the frontend
hash, all source hashes, logs, statuses, and resource samples. The complete
denominator report at `results/raw-diverse-v1/REPORT.md` records twelve
export-unavailable rows and zero solver attempts. No failed source was
silently replaced or excluded.

Raw export currently constructs the request-tracking Petri net and then fully
expands the serial automaton's Parikh image before writing either output.
Thus `--export-raw` avoids Petri-net reduction and complement construction,
but still depends on eager semilinear construction. Supporting these new
families requires a scalable exact representation of that serial target,
or a better exact construction. Merely raising the component limit exposes
exponential subset enumeration and is not a sound resource fix.
