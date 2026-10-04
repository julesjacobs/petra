#!/usr/bin/env python3
"""Freeze larger paired SER programs without collecting or solving their queries."""
import argparse
import hashlib
import json
from pathlib import Path

from generate_diverse_ser import aba, write_skew

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/diverse-ser-programs-v1"
OUTPUT = ROOT / "benchmarks/diverse-ser-scaling-v1"
RING_SITES = (5, 6)
EPOCH_MODULI = (9, 13, 17, 25, 33, 49)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def cases():
    for sites in RING_SITES:
        for protected in (False, True):
            name = f"write_skew_n{sites}_{'pairlocked' if protected else 'racy'}"
            yield dict(
                name=name, family="ring-write-skew", bridge=sites == 5,
                parameters=dict(sites=sites, pairlocked=protected),
                serializable=protected,
                argument="ordered-strict-two-phase-locking" if protected else "all-sites-leave-successfully",
                source_text=write_skew(sites, protected),
                structural_parameters=dict(
                    distinct_request_types=sites + 1,
                    shared_boolean_sites=sites,
                    shared_boolean_locks=sites if protected else 0,
                    global_valuation_upper_bound=2 ** (sites * (2 if protected else 1)),
                ),
            )
    for versions in EPOCH_MODULI:
        for validated in (False, True):
            name = f"optimistic_v{versions}_{'validated' if validated else 'aba'}"
            yield dict(
                name=name, family="optimistic-aba-validation", bridge=versions == 9,
                parameters=dict(versions=versions, validate_value=validated),
                serializable=validated,
                argument="successful-observation-is-zero" if validated else "odd-epoch-wrap-changes-value",
                source_text=aba(versions, validated),
                structural_parameters=dict(
                    distinct_request_types=2,
                    epoch_domain_size=versions,
                    value_domain_size=2,
                    global_valuation_upper_bound=2 * versions,
                    semantic_advance_cycle_length=2 * versions,
                ),
            )


def artifacts():
    original = json.loads((BASE / "manifest.json").read_text())
    original_hashes = {case["sha256"]: case for case in original["cases"]}
    files, records = {}, []
    for case in cases():
        source = case["name"] + ".ser"
        data = case["source_text"].encode()
        sha256 = digest(data)
        previous = original_hashes.get(sha256)
        if case["bridge"] != (previous is not None):
            raise ValueError("Bridge selection no longer matches the frozen original corpus.")
        if previous and (BASE / previous["source"]).read_bytes() != data:
            raise ValueError("An original bridge source changed after its manifest was frozen.")
        files[source] = data
        paired = case["name"].rsplit("_", 1)[0] + "_" + (
            "racy" if case["serializable"] else "pairlocked"
        ) if case["family"] == "ring-write-skew" else (
            case["name"].rsplit("_", 1)[0] + "_" + ("aba" if case["serializable"] else "validated")
        )
        records.append(dict(
            name=case["name"], source=source, sha256=sha256, bytes=len(data),
            family=case["family"], parameters=case["parameters"],
            structural_parameters=case["structural_parameters"], paired_with=paired,
            role="existing-development-bridge" if case["bridge"] else "parameter-scaling-development-case",
            exact_source_overlaps=[str((BASE / previous["source"]).relative_to(ROOT))] if previous else [],
            independent_test=False,
            source_expectation=dict(
                serializable=case["serializable"], argument=case["argument"],
                basis="source-level semantic argument; research/diverse-ser-programs-v1.md",
                mechanically_verified=False,
            ),
            export_result=None, solver_result=None,
        ))
    provenance = []
    for path in [Path(__file__), ROOT / "scripts/generate_diverse_ser.py",
                 BASE / "manifest.json", ROOT / "research/diverse-ser-programs-v1.md",
                 ROOT / "vendor/SerializabilityChecker/src/parser.rs"]:
        provenance.append(dict(path=str(path.resolve().relative_to(ROOT)), sha256=digest(path.read_bytes())))
    manifest = dict(
        format="ser-stress-sources-v1", version=1,
        selection="Fixed parameter ladder chosen before exporting or solving these larger instances; bridges are explicit duplicates.",
        corpus="diverse-ser-scaling-v1",
        counts=dict(sources=16, new_sources=12, existing_bridges=4,
                    expected_serializable=8, expected_nonserializable=8),
        axes=dict(
            ring_sites=list(RING_SITES), epoch_moduli=list(EPOCH_MODULI),
            request_multiplicity="unbounded at every parameter; no imposed concurrency bound",
            selection_reason="One additional ring size limits exponential frontend growth; five larger odd epoch domains vary serial-cycle length and interference needed for the ABA witness.",
        ),
        provenance=provenance, cases=records,
        limitations=[
            "New means a new source in this ladder, not an independent benchmark family.",
            "All cases are development relatives of the existing ring-write-skew and optimistic-aba-validation families.",
            "Source expectations are unproved by the toolchain and must not be counted as solved queries.",
            "Difficulty, export feasibility, and backend performance of the twelve larger sources are unmeasured at selection time.",
            "Global valuation bounds describe source data, not measured Petri-net sizes or reachable-state counts.",
            "Four bridges are exact duplicates and must not inflate the new-source denominator.",
            "Every attempted source, including export timeouts and memory limits, must remain in end-to-end reports.",
            "No reserved evaluation family is included.",
        ],
    )
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    files["SHA256SUMS"] = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(files.items())).encode()
    return files


def freeze(output):
    files = artifacts()
    if output.exists():
        if {p.name for p in output.iterdir()} != set(files) or any(
            not (output / name).is_file() or (output / name).read_bytes() != data
            for name, data in files.items()
        ):
            raise ValueError("Existing output differs; use a new directory to preserve the frozen corpus.")
        return False
    output.mkdir(parents=True)
    for name, data in files.items():
        (output / name).write_bytes(data)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        created = freeze(args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"{'Frozen' if created else 'Verified unchanged'} 12 new sources and 4 bridges: {args.output}")


if __name__ == "__main__":
    main()
