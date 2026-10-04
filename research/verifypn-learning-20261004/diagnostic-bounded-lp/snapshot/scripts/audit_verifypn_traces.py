#!/usr/bin/env python3
"""Replay archived VerifyPN traces against hash-checked, unreduced JSON nets."""

import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def checked_bytes(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"hash mismatch: {path}")
    return data


def predicate(node, marking):
    tag = node.tag.rsplit("}", 1)[-1]
    if tag == "integer-constant":
        return int(node.text)
    if tag == "tokens-count":
        return sum(marking[p.text] for p in node)
    children = [predicate(c, marking) for c in node]
    if tag == "integer-le":
        a, b = children
        return a <= b
    if tag == "conjunction":
        return all(children)
    if tag == "disjunction":
        return any(children)
    if tag == "negation":
        (value,) = children
        return not value
    if tag == "true":
        return True
    if tag == "false":
        return False
    raise ValueError(f"unsupported original predicate: {tag}")


def target_matches(rows, marking):
    for row in rows:
        value = sum(c * m for c, m in zip(row["coefficients"], marking, strict=True))
        if row.get("equality", False):
            if value != row["bound"]:
                return False
        elif value < row["bound"]:
            return False
    return True


def audit(query, root, log_path):
    text = log_path.read_text()
    result = {"query": query["name"], "kind": query["kind"], "log": str(log_path),
              "log_sha256": hashlib.sha256(text.encode()).hexdigest()}
    answer = re.findall(r"^FORMULA " + re.escape(query["property_id"]) + r" (TRUE|FALSE)\b", text, re.M)
    if len(answer) != 1:
        raise ValueError("missing or ambiguous property verdict")
    reachable = (answer[0] == "TRUE") == (query["kind"] == "EF")
    result["external_verdict"] = "reachable" if reachable else "unreachable"
    if not reachable:
        result["status"] = "external_negative_unchecked"
        return result
    traces = re.findall(r"<trace(?:\s[^>]*)?>.*?</trace>", text, re.S)
    if len(traces) != 1:
        raise ValueError("missing or ambiguous complete trace")
    trace = ET.fromstring(traces[0])
    if any(child.tag != "transition" for child in trace):
        raise ValueError("unsupported trace item")
    names = [t.attrib["id"] for t in trace]
    branches = [json.loads(checked_bytes(root / b["path"], b["sha256"])) for b in query["branches"]]
    if not branches:
        raise ValueError("no canonical net")
    net = branches[0]
    for branch in branches:
        if any(branch[k] != net[k] for k in ("places", "initial", "transitions")):
            raise ValueError("branch net mismatch")
    transitions = {t["name"]: t for t in net["transitions"]}
    if len(transitions) != len(net["transitions"]):
        raise ValueError("duplicate transition names")
    missing = sorted(set(names) - transitions.keys())
    if missing:
        raise ValueError(f"unexpanded or missing original transition names: {missing}")
    marking = list(net["initial"])
    # FIFO token matching characterizes one valid causal realization, not minimum depth.
    tokens = [deque([0] * m) for m in marking]
    depths = []
    target_places = {p for b in branches for row in b["target"]
                     for p, c in enumerate(row["coefficients"]) if c}
    unchanged_run = longest_unchanged = 0
    for step, name in enumerate(names, 1):
        t = transitions[name]
        pre, post = Counter(), Counter()
        for p, weight in t["pre"]:
            pre[p] += weight
        for p, weight in t["post"]:
            post[p] += weight
        if any(marking[p] < weight for p, weight in pre.items()):
            raise ValueError(f"disabled original transition at step {step}: {name}")
        consumed_depths = []
        for p, weight in pre.items():
            marking[p] -= weight
            consumed_depths.extend(tokens[p].popleft() for _ in range(weight))
        depth = 1 + max(consumed_depths, default=0)
        depths.append(depth)
        for p, weight in post.items():
            marking[p] += weight
            tokens[p].extend([depth] * weight)
        changes_target = any(post[p] != pre[p] for p in target_places)
        unchanged_run = 0 if changes_target else unchanged_run + 1
        longest_unchanged = max(longest_unchanged, unchanged_run)
    matched = [i for i, b in enumerate(branches) if target_matches(b["target"], marking)]
    if not matched:
        raise ValueError("trace endpoint misses every original canonical target")
    xml = ET.fromstring(checked_bytes(root / query["xml"], query["xml_sha256"]))
    for node in xml.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    prop, = xml.findall("property")
    if prop.findtext("id") != query["property_id"]:
        raise ValueError("original XML property ID mismatch")
    temporal, = list(prop.find("formula"))
    modality, = list(temporal)
    if (temporal.tag, modality.tag) != ({"EF": ("exists-path", "finally"),
                                       "AG": ("all-paths", "globally")}[query["kind"]]):
        raise ValueError("original XML temporal mode mismatch")
    condition, = list(modality)
    holds = predicate(condition, dict(zip(net["places"], marking, strict=True)))
    if holds != (query["kind"] == "EF"):
        raise ValueError("trace endpoint does not witness original XML property polarity")
    result.update(status="independently_replayed", length=len(names),
                  unique_transitions=len(set(names)), max_transition_count=max(Counter(names).values(), default=0),
                  fifo_causal_depth=max(depths, default=0), matched_branches=matched,
                  longest_target_place_plateau=longest_unchanged,
                  unindexed_trace_steps=sum("index" not in t.attrib for t in trace),
                  original_places=len(net["places"]), original_transitions=len(transitions))
    for pattern, key in [(r"Size of net after structural reductions: (\d+) places, (\d+) transitions", "reduced_net"),
                         (r"discovered states:\s*(\d+)", "discovered_states"),
                         (r"explored states:\s*(\d+)", "explored_states"),
                         (r"expanded states:\s*(\d+)", "expanded_states")]:
        found = re.search(pattern, text)
        if found:
            result[key] = [int(v) for v in found.groups()]
    result["reduction_rules"] = {rule: int(n) for rule, n in re.findall(r"Applications of rule ([A-Z]): (\d+)", text) if int(n)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    queries = {q["name"]: q for q in json.loads(args.manifest.read_text())["queries"]}
    results = []
    for item in json.loads(args.selection.read_text()):
        name = item["query"]
        try:
            results.append(audit(queries[name], args.manifest.parent, args.logs / f"{name}.verifypn.0.log"))
        except (ValueError, KeyError, OSError, ET.ParseError) as error:
            results.append({"query": name, "status": "replay_failed", "error": str(error)})
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(dict(Counter(r["status"] for r in results)), sort_keys=True))
    if any(r["status"] == "replay_failed" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
