"""Independent checking of original-property-v1 Rust PNML/XML answers.

Only run this validator in the bounded post-measurement worker. It translates
the original inputs independently and checks canonical branches and proofs.
"""
import math
from pathlib import Path

from bounded_validation import InputChecks, read_json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def aggregate(verdicts, branch_count):
    if "reachable" in verdicts:
        return "reachable"
    if len(verdicts) == branch_count and all(v == "unreachable" for v in verdicts):
        return "unreachable"
    return "unknown"


def truth(kind, verdict):
    if verdict == "unknown":
        return None
    return (verdict == "reachable") == (kind == "EF")


def validate(request):
    from benchmark import verify, DEFAULT_DAG_CHECK_WORK
    from native_original import translate

    require(__debug__, "certificate checking requires Python assertions enabled")

    unknown = dict(verdict="unknown", property_truth=None, independent_checks=[], branches=[])
    if request.get("outer_timeout", False):
        return dict(unknown, validation_skipped="solver-outer-timeout")
    require(request["exit_code"] == 0, f"Rust frontend exit code {request['exit_code']}")
    query = request["query"]
    corpus = Path(request["corpus"])
    summary = read_json(Path(request["log"]), request["response_bytes"])
    require(type(summary) is dict and summary.get("kind") == "original-property-v1", "wrong Rust output kind")
    require(summary.get("property_id") == query["property_id"], "property ID mismatch")
    require(summary.get("property_kind") == query["kind"] and query["kind"] in ("EF", "AG"), "property polarity mismatch")
    require(type(summary.get("branch_count")) is int and summary["branch_count"] == len(query["branches"]), "branch count mismatch")
    require(type(summary.get("deadline_exceeded")) is bool, "missing or invalid deadline flag")
    require(summary.get("verdict") in ("reachable", "unreachable", "unknown"), "invalid aggregate verdict")
    for field in ("parse_seconds", "solve_seconds"):
        value = summary.get(field)
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0, "invalid frontend timing")
    attempts = summary.get("attempts")
    require(type(attempts) is list and len(attempts) <= summary["branch_count"], "invalid attempts")
    declared = []
    for index, attempt in enumerate(attempts):
        require(type(attempt) is dict and type(attempt.get("branch")) is int and attempt["branch"] == index,
                "attempts must form a contiguous branch prefix")
        answer = attempt.get("outcome")
        require(type(answer) is dict and answer.get("verdict") in ("reachable", "unreachable", "unknown"),
                "invalid branch outcome")
        require(type(answer.get("method")) is str, "missing branch method")
        require("reachable" not in declared, "attempt occurs after reachable branch")
        declared.append(answer["verdict"])
    claimed = "unknown" if summary["deadline_exceeded"] else aggregate(declared, len(query["branches"]))
    require(summary["verdict"] == claimed, "aggregate verdict disagrees with branch coverage")
    require(summary.get("property_truth") is truth(query["kind"], claimed), "property truth mismatch")

    hashes = InputChecks()
    for field in ("pnml", "xml"):
        hashes.check(corpus / query[field], query[field + "_sha256"])
    net, prop = translate(corpus / query["pnml"], corpus / query["xml"], query["property_id"])
    for transition in net["transitions"]:
        for field in ("pre", "post"):
            transition[field] = [list(arc) for arc in transition[field]]
    require(prop["kind"] == query["kind"] and len(prop["targets"]) == len(query["branches"]),
            "original XML polarity or branch count disagrees with canonical metadata")
    checks, branches, verified = [], [], []
    for index, branch in enumerate(query["branches"]):
        path = corpus / branch["path"]
        hashes.check(path, branch["sha256"])
        problem = read_json(path)
        require(problem == dict(net, target=prop["targets"][index]),
                f"canonical branch {index} disagrees with independently translated original input")
        if index >= len(attempts):
            continue
        answer = attempts[index]["outcome"]
        verdict = answer["verdict"]
        result = dict(branch=index, verdict=verdict, engine=answer["method"])
        if verdict == "reachable":
            require(type(answer.get("trace")) is list and all(type(t) is int for t in answer["trace"]), "invalid witness trace")
            marking = answer.get("marking")
            require(marking is None or (type(marking) is list and all(type(x) is int and 0 <= x < 2**64 for x in marking)),
                    "invalid witness marking")
        check = verify(problem, answer, dag_max_work=request.get("dag_check_max_work", DEFAULT_DAG_CHECK_WORK))
        checks.append(check)
        result["independent_check"] = check
        if verdict != "unknown" and not check.startswith("python-"):
            result["unchecked_verdict"] = verdict
            result["verdict"] = "unknown"
        verified.append(result["verdict"])
        branches.append(result)
    hashes.unchanged()
    verdict = "unknown" if summary["deadline_exceeded"] else aggregate(verified, len(query["branches"]))
    return dict(verdict=verdict, property_truth=truth(query["kind"], verdict), independent_checks=checks,
                branches=branches, deadline_exceeded=summary["deadline_exceeded"],
                translation_check="independent-original-input-equals-all-canonical-branches",
                rust_parse_seconds=summary["parse_seconds"], rust_solve_seconds=summary["solve_seconds"])
