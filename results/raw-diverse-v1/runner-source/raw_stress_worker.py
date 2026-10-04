#!/usr/bin/env python3
"""Bounded-worker entry point for raw-query validation, solving, and witness checking.

The parent must enforce the outer wall/RSS limits on this worker and descendants.
Accept positives by original-net replay and serial nonmembership, and negatives
by independently checked controller-indexed serial-component invariants.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

U64_MAX = 2**64 - 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON field: {key}")
        result[key] = value
    return result


def load_json(path):
    def reject_constant(value):
        raise ValueError(f"invalid JSON constant: {value}")
    with Path(path).open() as stream:
        return json.load(stream, object_pairs_hook=unique_object, parse_constant=reject_constant)


def validate(q):
    require(type(q) is dict and q.get("format") == "ser-raw-v1", "unsupported raw format")
    places = q["places"]
    require(type(places) is list and all(type(p) is str for p in places), "invalid places")
    n = len(places)
    initial = q["initial"]
    require(type(initial) is list and len(initial) == n, "initial dimension mismatch")
    require(all(type(x) is int and 0 <= x <= U64_MAX for x in initial), "invalid initial marking")

    def indices(xs):
        require(type(xs) is list and all(type(x) is int and 0 <= x < n for x in xs), "invalid place index")
        require(len(set(xs)) == len(xs), "repeated place index")

    def arcs(xs, allowed):
        require(type(xs) is list, "arc vector must be a list")
        seen = set()
        for arc in xs:
            require(type(arc) is list and len(arc) == 2, "invalid arc pair")
            p, w = arc
            require(type(p) is int and p in allowed and p not in seen, "invalid or repeated arc place")
            require(type(w) is int and 0 < w <= U64_MAX, "invalid arc weight")
            seen.add(p)

    target = q["target"]
    require(type(target) is dict and target.get("kind") == "completed-outside-semilinear", "invalid target kind")
    indices(target["zero_places"])
    indices(target["response_places"])
    require(not set(target["zero_places"]) & set(target["response_places"]), "overlapping target places")
    require(type(q["transitions"]) is list, "invalid transitions")
    for t in q["transitions"]:
        require(type(t) is dict and type(t["name"]) is str, "invalid transition")
        arcs(t["pre"], range(n))
        arcs(t["post"], range(n))
    require(type(target["excluded_semilinear"]) is list, "invalid serial union")
    responses = set(target["response_places"])
    for c in target["excluded_semilinear"]:
        require(type(c) is dict and type(c["periods"]) is list, "invalid linear set")
        arcs(c["base"], responses)
        for period in c["periods"]:
            arcs(period, responses)


class VerificationUnknown(Exception):
    pass


def verify_positive(q, answer, deadline, z3_module=None):
    require(answer.get("verdict") == "reachable", "not a positive answer")
    require(type(answer.get("trace")) is list, "missing transition trace")
    marking = q["initial"][:]
    for step, index in enumerate(answer["trace"]):
        if time.monotonic() >= deadline:
            raise VerificationUnknown("witness replay deadline")
        require(type(index) is int and 0 <= index < len(q["transitions"]), f"invalid transition at step {step}")
        t = q["transitions"][index]
        require(all(marking[p] >= w for p, w in t["pre"]), f"disabled transition at step {step}")
        for p, w in t["pre"]:
            marking[p] -= w
        for p, w in t["post"]:
            marking[p] += w
            require(marking[p] <= U64_MAX, "witness counter overflow")
    claimed = answer.get("marking")
    require(type(claimed) is list and all(type(x) is int for x in claimed) and claimed == marking,
            "reported marking differs from original replay")
    require(all(marking[p] == 0 for p in q["target"]["zero_places"]), "witness is incomplete")
    if z3_module is None:
        import z3 as z3_module
    z3 = z3_module
    for component, linear in enumerate(q["target"]["excluded_semilinear"]):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise VerificationUnknown("serial membership verification deadline")
        base = dict(linear["base"])
        periods = linear["periods"]
        ns = [z3.Int(f"k_{i}") for i in range(len(periods))]
        terms = {}
        for k, period in zip(ns, periods):
            if time.monotonic() >= deadline:
                raise VerificationUnknown("serial formula construction deadline")
            for p, weight in period:
                terms.setdefault(p, []).append(k * weight)
        solver = z3.Solver()
        solver.add(*[k >= 0 for k in ns])
        solver.add(*[marking[p] == base.get(p, 0) + sum(terms.get(p, []))
                     for p in q["target"]["response_places"]])
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise VerificationUnknown("serial formula construction deadline")
        solver.set(timeout=max(1, int(remaining * 1000)))
        verdict = solver.check()
        if verdict == z3.unknown:
            raise VerificationUnknown(f"Z3 returned unknown on serial component {component}: {solver.reason_unknown()}")
        require(verdict == z3.unsat, f"witness belongs to serial component {component}")
    if time.monotonic() >= deadline:
        raise VerificationUnknown("verification deadline")
    return "python-original-replay-z3-nonmembership"


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def execute(args):
    deadline = time.monotonic() + args.seconds
    result = dict(verdict="unknown", status="worker-error")

    def stage(name):
        result["stage"] = name
        write_json(args.directory / "progress.json", dict(stage=name))

    try:
        stage("input-validation")
        require(sha256(args.query) == args.sha256, "input hash changed")
        q = load_json(args.query)
        validate(q)
        require(sha256(args.query) == args.sha256, "input hash changed during parsing")
        result["input"] = dict(places=len(q["places"]), transitions=len(q["transitions"]),
                               serial_components=len(q["target"]["excluded_semilinear"]))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise VerificationUnknown("input validation deadline")
        stage("solver")
        solver_seconds = remaining * args.solver_fraction
        command = ([sys.executable, str(args.raw_z3), str(args.query), "--seconds", str(solver_seconds)]
                   if args.method == "raw-z3" else
                   [str(args.binary), "--raw", str(args.query), "--method", args.method,
                    "--seconds", str(solver_seconds), "--max-states", str(args.max_states)])
        write_json(args.directory / "solver-command.json", command)
        with (args.directory / "solver.stdout").open("w") as stdout, (args.directory / "solver.stderr").open("w") as stderr:
            try:
                process = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=solver_seconds, check=False)
            except subprocess.TimeoutExpired:
                result.update(status="solver-timeout", reason="solver phase deadline")
                return result
        result["solver_exit_code"] = process.returncode
        if process.returncode != 0:
            result.update(status="solver-error", reason="nonzero solver exit")
            return result
        stage("answer-validation")
        answer = load_json(args.directory / "solver.stdout")
        require(type(answer) is dict, "answer must be an object")
        result["claimed_verdict"] = answer.get("verdict")
        if answer.get("verdict") == "unknown":
            result.update(status="solver-unknown", reason=str(answer.get("reason", "solver returned unknown"))[:1000])
        elif answer.get("verdict") == "unreachable":
            proof = answer.get("proof")
            if type(proof) is dict and proof.get("format") == "raw-component-invariant-v1":
                from raw_invariant_check import verify
                stage("negative-verification")
                result["verification_work_limit"] = args.max_states * 100
                result["independent_check"] = verify(q, proof, deadline, max_obligations=result["verification_work_limit"])
                result.update(verdict="unreachable", status="verified-negative")
            else:
                result.update(status="unsupported-negative", reason="missing or unsupported raw negative proof")
        else:
            stage("positive-verification")
            result["independent_check"] = verify_positive(q, answer, deadline)
            result.update(verdict="reachable", status="verified-positive", trace_length=len(answer["trace"]))
    except (VerificationUnknown, TimeoutError) as error:
        result.update(status="verification-unknown", reason=str(error))
    except (ValueError, KeyError, TypeError, IndexError, OSError, RecursionError) as error:
        status = "input-invalid" if result.get("stage") == "input-validation" else "invalid-answer"
        result.update(status=status, reason=f"{type(error).__name__}: {error}"[:2000])
    except Exception as error:
        result.update(status="worker-error", reason=f"{type(error).__name__}: {error}"[:2000])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--raw-z3", type=Path, required=True)
    parser.add_argument("--method", choices=["raw-bfs", "raw-search", "raw-potential", "raw-negative", "raw-portfolio", "raw-z3"], required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--solver-fraction", type=float, default=0.8)
    parser.add_argument("--max-states", type=int, default=200_000)
    args = parser.parse_args()
    require(0 < args.solver_fraction < 1 and 0 < args.seconds < float("inf"), "invalid deadline allocation")
    write_json(args.directory / "result.json", execute(args))


if __name__ == "__main__":
    main()
