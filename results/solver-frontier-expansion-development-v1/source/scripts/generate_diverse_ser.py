#!/usr/bin/env python3
"""Freeze finite-data SER families with write skew and optimistic ABA validation."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def request(name, lines):
    return "request " + name + " {\n    " + ";\n    ".join(lines) + "\n}\n"


def with_locks(lines, resources):
    prefix = []
    for resource in sorted(resources):
        prefix.extend([f"while (Lock{resource} == 1) {{ yield }}", f"Lock{resource} := 1"])
    suffix = [f"Lock{resource} := 0" for resource in reversed(sorted(resources))]
    return prefix + lines[:-1] + ["answer := " + lines[-1]] + suffix + ["answer"]


def write_skew(sites, protected):
    if sites < 3:
        raise ValueError("A ring needs at least three sites.")
    programs = []
    for site in range(sites):
        neighbor = (site + 1) % sites
        lines = [
            f"allowed := (Off{site} == 0) && (Off{neighbor} == 0)",
            "yield",
            f"if (allowed) {{ Off{site} := 1; 1 }} else {{ 0 }}",
        ]
        if protected:
            lines = with_locks(lines, [site, neighbor])
        programs.append(request(f"leave{site}", lines))
    reset = [f"Off{site} := 0" for site in range(sites)] + ["0"]
    if protected:
        reset = with_locks(reset, list(range(sites)))
    programs.append(request("reset", reset))
    return "\n".join(programs)


def aba(versions, validated):
    if versions < 3 or versions % 2 == 0:
        raise ValueError("The epoch modulus must be odd and at least three.")
    advance = [
        "Value := 1 - Value",
        f"if (Epoch == {versions - 1}) {{ Epoch := 0 }} else {{ Epoch := Epoch + 1 }}",
        "0",
    ]
    condition = "Epoch == epoch"
    if validated:
        condition = "(Epoch == epoch) && (after == before)"
    body = [
        "before := Value", "epoch := Epoch", "yield", "after := Value",
        f"if ({condition}) {{ done := 1 }} else {{ yield }}",
    ]
    read = ["done := 0", "while (done == 0) { " + "; ".join(body) + " }", "after - before"]
    return request("advance", advance) + "\n" + request("observe", read)


def cases():
    for sites in [3, 4, 5]:
        for protected in [False, True]:
            variant = "pairlocked" if protected else "racy"
            yield dict(name=f"write_skew_n{sites}_{variant}", family="ring-write-skew",
                       parameters=dict(sites=sites, pairlocked=protected),
                       serializable=protected,
                       argument="ordered-strict-two-phase-locking" if protected else "all-sites-leave-successfully",
                       source_text=write_skew(sites, protected))
    for versions in [3, 5, 9]:
        for validated in [False, True]:
            variant = "validated" if validated else "aba"
            yield dict(name=f"optimistic_v{versions}_{variant}", family="optimistic-aba-validation",
                       parameters=dict(versions=versions, validate_value=validated),
                       serializable=validated,
                       argument="successful-observation-is-zero" if validated else "odd-epoch-wrap-changes-value",
                       source_text=aba(versions, validated))


def artifacts():
    files, records = {}, []
    for case in cases():
        data = case["source_text"].encode()
        source = case["name"] + ".ser"
        files[source] = data
        records.append(dict(name=case["name"], source=source, sha256=digest(data), bytes=len(data),
                            family=case["family"], parameters=case["parameters"],
                            role="new-mechanism-development-case", exact_source_overlaps=[],
                            independent_test=False,
                            source_expectation=dict(serializable=case["serializable"],
                                argument=case["argument"],
                                basis="source-level semantic argument; research/diverse-ser-programs-v1.md",
                                mechanically_verified=False), solver_result=None))
    provenance = []
    for path in [Path(__file__), ROOT / "research/diverse-ser-programs-v1.md",
                 ROOT / "vendor/SerializabilityChecker/src/parser.rs"]:
        provenance.append(dict(path=str(path.resolve().relative_to(ROOT)), sha256=digest(path.read_bytes())))
    manifest = dict(format="ser-stress-sources-v1", version=1,
                    selection="fixed parameter ladders for two new synchronization mechanisms; no solver-outcome selection",
                    provenance=provenance, cases=records,
                    limitations=["Source expectations are arguments, not solver ground truth or exported-net proofs.",
                                 "Difficulty and raw-export feasibility are unmeasured.",
                                 "Parameter relatives are correlated development data, not held-out evaluation.",
                                 "The source language has finite data but unbounded request multiplicity.",
                                 "Export failures must remain in the source-level denominator."])
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
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/diverse-ser-programs-v1")
    args = parser.parse_args()
    try:
        created = freeze(args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"{'Frozen' if created else 'Verified unchanged'} 12 sources: {args.output}")


if __name__ == "__main__":
    main()
