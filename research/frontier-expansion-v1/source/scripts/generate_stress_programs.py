#!/usr/bin/env python3
"""Freeze a deterministic SER stress ladder without exporting reachability queries."""
import argparse
import hashlib
import json
from pathlib import Path

import generate_harder

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def cases():
    for domain, stages in [(31, 16), (63, 32), (127, 64)]:
        for locked in [False, True]:
            name = f"counter_d{domain}_s{stages}_{'locked' if locked else 'racy'}"
            yield name, "cyclic-counter", dict(domain=domain, stages=stages, locked=locked), locked, \
                generate_harder.counter(domain, stages, locked), \
                "lock-linearization" if locked else "two-increments-return-one", None
    for cells in [8, 10, 12]:
        for locked in [False, True]:
            name = f"replicas_n{cells}_{'locked' if locked else 'racy'}"
            yield name, "replicated-register", dict(cells=cells, locked=locked), locked, \
                generate_harder.replicas(cells, locked), \
                "lock-linearization" if locked else "read-torn-write", None
    for domain, cycles in [(4, 64), (4, 128), (4, 256), (5, 128), (5, 256), (5, 512)]:
        yield f"monitor_d{domain}_c{cycles}", "phase-monitor", dict(domain=domain, cycles=cycles), False, \
            generate_harder.monitor(domain, cycles), \
            "observe-completes-only-with-interleaved-advances", domain * cycles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/stress-programs")
    args = parser.parse_args()
    prior = {}
    for directory in ["harder-programs", "scaling-programs"]:
        for path in sorted((ROOT / "benchmarks" / directory).glob("*.ser")):
            prior.setdefault(digest(path.read_bytes()), []).append(str(path.relative_to(ROOT)))
    files, records = {}, []
    for name, family, parameters, serializable, source, argument, advances in cases():
        data = source.encode()
        sha = digest(data)
        overlaps = prior.get(sha, [])
        files[name + ".ser"] = data
        records.append(dict(name=name, source=name + ".ser", sha256=sha, bytes=len(data),
                            family=family, parameters=parameters,
                            role="bridge" if overlaps else "new-scaling-case",
                            exact_source_overlaps=overlaps,
                            independent_test=False,
                            source_expectation=dict(serializable=serializable,
                                argument=argument,
                                basis="source-level semantic argument; research/harder-programs.md",
                                mechanically_verified=False,
                                minimum_advance_requests_for_observe_response=advances),
                            solver_result=None))
    provenance = []
    for path in [Path(__file__), ROOT / "scripts/generate_harder.py", ROOT / "research/harder-programs.md"]:
        provenance.append(dict(path=str(path.resolve().relative_to(ROOT)), sha256=digest(path.read_bytes())))
    manifest = dict(format="ser-stress-sources-v1", version=1,
                    selection="fixed deterministic scaling ladder; no solver-outcome selection",
                    provenance=provenance, cases=records,
                    limitations=["Source expectations are not solver results or exported-net proofs.",
                                 "Scaling relatives are correlated; bridge cases duplicate earlier sources.",
                                 "Frontend semilinear construction may exhaust resources before a query exists.",
                                 "Monitor advancement bounds count source requests, not Petri-net transitions."])
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    files["SHA256SUMS"] = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(files.items())).encode()
    if args.output.exists():
        if {p.name for p in args.output.iterdir()} != set(files):
            raise SystemExit("Existing output differs; use a new directory to preserve the frozen corpus.")
        if any((args.output / name).read_bytes() != data for name, data in files.items()):
            raise SystemExit("Existing output differs; use a new directory to preserve the frozen corpus.")
        print(f"Verified unchanged frozen sources: {args.output}")
        return
    args.output.mkdir(parents=True)
    for name, data in files.items():
        (args.output / name).write_bytes(data)
    print(f"Frozen {len(records)} sources ({sum(r['role'] == 'bridge' for r in records)} bridges): {args.output}")


if __name__ == "__main__":
    main()
