#!/usr/bin/env python3
"""Replay frozen count boxes; this diagnostic never invokes a solver."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time


@dataclass(frozen=True)
class Limits:
    states: int = 200_000
    work: int = 20_000_000
    seconds: float = 10.0
    cells: int = 16_000_000


class Limited(Exception):
    pass


class Budget:
    def __init__(self, limits):
        self.limits = limits
        self.start = time.monotonic()
        self.work = 0

    def charge(self, amount=1):
        if self.work + amount > self.limits.work:
            raise Limited("work")
        self.work += amount
        if time.monotonic() - self.start >= self.limits.seconds:
            raise Limited("wall")

    def allocate(self, nodes, width):
        self.charge()
        if nodes >= self.limits.states:
            raise Limited("states")
        if (nodes + 1) * width > self.limits.cells:
            raise Limited("cells")


@dataclass
class Node:
    marking: tuple
    remaining: tuple
    parent: tuple | None


def accepts(problem, marking, budget):
    for constraint in problem["target"]:
        budget.charge(len(marking) + 1)
        value = sum(a * n for a, n in zip(constraint["coefficients"], marking))
        if constraint["equality"]:
            if value != constraint["bound"]:
                return False
        elif value < constraint["bound"]:
            return False
    return True


def enabled(transition, marking, budget):
    budget.charge(len(transition["pre"]) + 1)
    return all(marking[q] >= n for q, n in transition["pre"])


def fire(transition, marking, budget):
    budget.charge(len(marking) + len(transition["pre"]) + len(transition["post"]))
    result = list(marking)
    for q, n in transition["pre"]:
        result[q] -= n
    for q, n in transition["post"]:
        result[q] += n
    return tuple(result)


def dominates(left, right, budget):
    budget.charge(len(left) + 1)
    return all(a >= b for a, b in zip(left, right))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def replay(problem, counts, dominance=False, limits=Limits()):
    budget = Budget(limits)
    nodes = []
    pending = []
    antichains = {}
    seen = set()
    frontier = set()
    dominated_prefixes = 0
    removed_representatives = 0
    duplicate_prefixes = 0
    expanded = 0
    peak_width = 0
    witness = None
    status = "incomplete"
    reason = None
    width = max(1, len(problem["places"]) + len(counts))
    try:
        budget.allocate(0, width)
        first = Node(tuple(problem["initial"]), tuple(counts), None)
        nodes.append(first)
        pending.append(0)
        seen.add(first.remaining)
        antichains[first.marking] = [0]
        peak_width = 1
        while pending:
            budget.charge()
            index = pending.pop()
            node = nodes[index]
            if dominance and index not in antichains[node.marking]:
                continue
            expanded += 1
            if accepts(problem, node.marking, budget):
                witness = []
                cursor = index
                while nodes[cursor].parent is not None:
                    budget.charge()
                    cursor, transition = nodes[cursor].parent
                    witness.append(transition)
                witness.reverse()
                status = "witness"
                break
            for t in reversed(range(len(problem["transitions"]))):
                transition = problem["transitions"][t]
                if not enabled(transition, node.marking, budget):
                    continue
                if node.remaining[t] == 0:
                    frontier.add(t)
                    continue
                rest = list(node.remaining)
                rest[t] -= 1
                rest = tuple(rest)
                budget.charge(len(rest))
                if rest in seen:
                    duplicate_prefixes += 1
                    continue
                marking = fire(transition, node.marking, budget)
                representatives = antichains.get(marking, [])
                if dominance and any(dominates(nodes[i].remaining, rest, budget)
                                     for i in representatives):
                    dominated_prefixes += 1
                    continue
                if dominance:
                    keep = [i for i in representatives
                            if not dominates(rest, nodes[i].remaining, budget)]
                else:
                    keep = list(representatives)
                budget.allocate(len(nodes), width)
                removed_representatives += len(representatives) - len(keep)
                keep.append(len(nodes))
                antichains[marking] = keep
                peak_width = max(peak_width, len(keep))
                seen.add(rest)
                pending.append(len(nodes))
                nodes.append(Node(marking, rest, (index, t)))
        else:
            # Removed representatives can have weaker frontier information.
            frontier = set()
            for marking, indices in antichains.items():
                for i in indices:
                    for t, transition in enumerate(problem["transitions"]):
                        if nodes[i].remaining[t] == 0 and enabled(transition, marking, budget):
                            frontier.add(t)
            status = "complete"
    except Limited as error:
        reason = str(error)
    result = {
        "status": status,
        "limit": reason,
        "nodes": len(nodes),
        "expanded_nodes": expanded,
        "distinct_markings": len(antichains),
        "duplicate_prefixes": duplicate_prefixes,
        "dominated_prefixes": dominated_prefixes,
        "removed_representatives": removed_representatives,
        "retained_representatives": sum(map(len, antichains.values())),
        "peak_vectors_per_marking": peak_width,
        "final_vectors_per_marking": max(map(len, antichains.values()), default=0),
        "work": budget.work,
        "seconds": time.monotonic() - budget.start,
        "frontier": [[t, counts[t]] for t in sorted(frontier)] if status == "complete" else None,
        "witness": witness,
    }
    return result, nodes, antichains


def independently_check(problem, counts, baseline, candidate, limits=Limits()):
    """Check a finite simulation certificate using direct integer operations."""
    budget = Budget(limits)
    reference, original, _ = baseline
    result, nodes, antichains = candidate
    try:
        budget.charge()
        transitions = problem["transitions"]
        places = len(problem["places"])
        require(len(counts) == len(transitions), "invalid count dimension")
        require(all(type(n) is int and n >= 0 for n in counts), "invalid count bound")
        if result["status"] == "incomplete":
            return {"status": "incomplete", "limit": "exploration incomplete"}
        if result["status"] == "witness":
            marking = list(problem["initial"])
            uses = [0] * len(counts)
            for t in result["witness"]:
                require(type(t) is int and 0 <= t < len(transitions), "invalid witness transition")
                transition = problem["transitions"][t]
                budget.charge(len(transition["pre"]) + len(transition["post"]) + 1)
                require(all(marking[q] >= n for q, n in transition["pre"]), "disabled witness step")
                for q, n in transition["pre"]:
                    marking[q] -= n
                for q, n in transition["post"]:
                    marking[q] += n
                uses[t] += 1
            require(all(x <= y for x, y in zip(uses, counts)), "witness exceeds count bounds")
            for c in problem["target"]:
                budget.charge(len(marking))
                value = sum(a * n for a, n in zip(c["coefficients"], marking))
                require(value == c["bound"] if c["equality"] else value >= c["bound"],
                        "witness misses target")
            return {"status": "passed", "kind": "witness", "work": budget.work}

        require(result["status"] == "complete", "invalid exploration status")
        if reference["status"] != "complete":
            return {"status": "incomplete", "limit": "baseline exploration incomplete"}
        require(set(map(tuple, result["frontier"])) <= set(map(tuple, reference["frontier"])),
                "frontier is not a subset of original frontier")
        require(antichains, "missing retained states")
        for marking, indices in antichains.items():
            budget.charge(places + len(indices) + 1)
            require(len(marking) == places and all(type(n) is int and n >= 0 for n in marking),
                    "invalid marking")
            require(indices and len(set(indices)) == len(indices), "invalid representative list")
            for i in indices:
                require(type(i) is int and 0 <= i < len(nodes), "invalid representative index")
                node = nodes[i]
                budget.charge(len(counts) + places + 1)
                require(node.marking == marking, "representative marking differs from its key")
                require(len(node.remaining) == len(counts), "invalid remaining dimension")
                require(all(type(r) is int and 0 <= r <= n for r, n in zip(node.remaining, counts)),
                        "remaining count outside bounds")
                expected = list(problem["initial"])
                for t, transition in enumerate(transitions):
                    used = counts[t] - node.remaining[t]
                    budget.charge(len(transition["pre"]) + len(transition["post"]) + 1)
                    for q, n in transition["pre"]:
                        expected[q] -= used * n
                    for q, n in transition["post"]:
                        expected[q] += used * n
                require(tuple(expected) == marking, "representative violates state equation")
        require(any(nodes[i].remaining == tuple(counts)
                    for i in antichains.get(tuple(problem["initial"]), [])),
                "missing initial remaining-count vector")
        for original_node in original:
            covered = False
            for i in antichains.get(original_node.marking, []):
                budget.charge(len(counts) + 1)
                if all(a >= b for a, b in zip(nodes[i].remaining, original_node.remaining)):
                    covered = True
                    break
            require(covered, "original prefix has no retained dominating representative")
        found_frontier = set()
        for marking, indices in antichains.items():
            for i in indices:
                node = nodes[i]
                target_holds = True
                for c in problem["target"]:
                    budget.charge(len(marking) + 1)
                    value = sum(a * n for a, n in zip(c["coefficients"], marking))
                    target_holds &= value == c["bound"] if c["equality"] else value >= c["bound"]
                require(not target_holds, "retained state reaches target")
                for t, transition in enumerate(problem["transitions"]):
                    budget.charge(len(transition["pre"]) + 1)
                    if any(marking[q] < n for q, n in transition["pre"]):
                        continue
                    if node.remaining[t] == 0:
                        found_frontier.add((t, counts[t]))
                        continue
                    after = list(marking)
                    rest = list(node.remaining)
                    rest[t] -= 1
                    budget.charge(len(marking) + len(rest) + len(transition["post"]))
                    for q, n in transition["pre"]:
                        after[q] -= n
                    for q, n in transition["post"]:
                        after[q] += n
                    covered = False
                    for j in antichains.get(tuple(after), []):
                        budget.charge(len(counts) + 1)
                        if all(a >= b for a, b in zip(nodes[j].remaining, rest)):
                            covered = True
                            break
                    require(covered, "retained execution graph lacks simulation closure")
        require(found_frontier == set(map(tuple, result["frontier"])), "incorrect frontier")
        return {"status": "passed", "kind": "finite-simulation", "work": budget.work}
    except Limited as error:
        return {"status": "incomplete", "limit": str(error), "work": budget.work}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    source = root / "research/frontier-sequences-v1"
    old_plan = json.loads((source / "plan.json").read_text())
    runs = [json.loads(line) for line in (source / "runs.jsonl").read_text().splitlines()]
    require(len(runs) == 5, "expected five frozen logs")
    limits = Limits()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name in ("plan.json", "events.jsonl", "result.json"):
        if (output / name).exists():
            raise ValueError(f"refusing to overwrite {output / name}")
    plan = {
        "scope": "Frozen-event mechanism diagnostic; no fresh solver proposals or property verdicts.",
        "limits_per_exploration_and_independent_check": asdict(limits),
        "work_units": "Upper-bound charged scalar slots in guard, target, state and dominance operations.",
        "semantics": "Unbounded mathematical nonnegative integers; pinned graphs are small and match Rust logs.",
        "sources": {str(path.relative_to(root)): sha(path) for path in
                    [Path(__file__).resolve(), Path(__file__).with_name("test_diagnostic.py").resolve(),
                     source / "plan.json", source / "runs.jsonl"]},
        "inputs": old_plan["inputs"],
        "logs": {row["log"]: row["log_sha256"] for row in runs},
        "iteration": "Same reversed-transition DFS order; original count-vector dedup versus marking antichains.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    branches = []
    with (output / "events.jsonl").open("w") as stream:
        for run in runs:
            input_path = root / run["input"]
            log_path = source / run["log"]
            require(sha(input_path) == old_plan["inputs"][run["input"]], "input hash mismatch")
            require(sha(log_path) == run["log_sha256"], "log hash mismatch")
            problem = json.loads(input_path.read_text())
            summary = dict(input=run["input"], log=run["log"], events=0, paired_complete=0,
                           incomplete=0, baseline_nodes=0, dominance_nodes=0,
                           baseline_distinct_markings=0, dominance_distinct_markings=0,
                           dominated_prefixes=0, removed_representatives=0,
                           node_reduction_events=0, changed_frontiers=0,
                           maximum_antichain_width=0, checks_passed=0)
            cumulative = 0
            for line_number, line in enumerate(log_path.read_text().splitlines(), 1):
                event = json.loads(line)
                if event.get("event") != "execution-frontier":
                    continue
                counts = [0] * len(problem["transitions"])
                previous = -1
                for t, count in event["counts"]:
                    require(previous < t < len(counts) and type(count) is int and count > 0,
                            "invalid sparse count vector")
                    counts[t] = count
                    previous = t
                baseline = replay(problem, counts, False, limits)
                candidate = replay(problem, counts, True, limits)
                exact, reduced = baseline[0], candidate[0]
                log_check = "incomplete"
                if exact["status"] == "complete":
                    require(exact["frontier"] == event["frontier"], "frozen frontier mismatch")
                    require(exact["nodes"] == event["states"] - cumulative, "frozen state count mismatch")
                    log_check = "passed"
                cumulative = event["states"]
                require(exact["status"] != "witness", "logged cut admits a witness")
                require(reduced["status"] != "witness", "dominance found a witness in a logged empty box")
                check = independently_check(problem, counts, baseline, candidate, limits)
                row = dict(input=run["input"], log=run["log"], line=line_number,
                           model=event["model"], logged_cumulative_states=event["states"],
                           log_check=log_check, baseline=exact, dominance=reduced, check=check)
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                stream.flush()
                summary["events"] += 1
                if log_check == "passed" and check["status"] == "passed":
                    summary["checks_passed"] += 1
                if exact["status"] == reduced["status"] == "complete":
                    summary["paired_complete"] += 1
                    summary["baseline_nodes"] += exact["nodes"]
                    summary["dominance_nodes"] += reduced["nodes"]
                    summary["baseline_distinct_markings"] += exact["distinct_markings"]
                    summary["dominance_distinct_markings"] += reduced["distinct_markings"]
                    summary["dominated_prefixes"] += reduced["dominated_prefixes"]
                    summary["removed_representatives"] += reduced["removed_representatives"]
                    summary["node_reduction_events"] += reduced["nodes"] < exact["nodes"]
                    summary["changed_frontiers"] += reduced["frontier"] != exact["frontier"]
                    summary["maximum_antichain_width"] = max(summary["maximum_antichain_width"],
                                                             reduced["peak_vectors_per_marking"])
                else:
                    summary["incomplete"] += 1
            branches.append(summary)
            print(json.dumps(summary), flush=True)
    keys = [key for key in branches[0] if key not in ("input", "log", "maximum_antichain_width")]
    totals = {key: sum(branch[key] for branch in branches) for key in keys}
    totals["maximum_antichain_width"] = max(branch["maximum_antichain_width"] for branch in branches)
    result = dict(scope=plan["scope"], plan_sha256=sha(output / "plan.json"),
                  events_sha256=sha(output / "events.jsonl"), branches=branches, totals=totals,
                  interpretation="Counts measure replayed graph structure, not solver coverage or speed.")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"totals": totals}))


if __name__ == "__main__":
    main()
