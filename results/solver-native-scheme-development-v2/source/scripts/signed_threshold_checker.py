"""Independent exact checker for supplied signed-threshold invariants."""

import time


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, lower, upper):
    return type(value) is int and lower <= value < upper


def _decimal(value, tick):
    _require(type(value) is str and value, "expected decimal string")
    digits = value[1:] if value[0] in "+-" else value
    _require(digits, "invalid decimal integer")
    # Chunk conversion avoids Python's configurable decimal-string length limit.
    result = 0
    for start in range(0, len(digits), 1000):
        tick()
        chunk = digits[start:start + 1000]
        _require(all("0" <= digit <= "9" for digit in chunk), "invalid decimal integer")
        result = result * 10 ** len(chunk) + int(chunk)
    tick()
    return -result if value[0] == "-" else result


def _validate_problem(problem, tick):
    _require(type(problem) is dict and all(key in problem for key in
             ("places", "initial", "transitions", "target")), "invalid problem fields")
    _require(type(problem["places"]) is list and
             all(type(name) is str for name in problem["places"]), "invalid places")
    n = len(problem["places"])
    initial = problem["initial"]
    _require(type(initial) is list and len(initial) == n, "invalid initial dimension")
    for value in initial:
        tick()
        _require(_integer(value, 0, 2**64), "invalid initial value")
    _require(type(problem["transitions"]) is list, "invalid transition list")
    for transition in problem["transitions"]:
        tick()
        _require(type(transition) is dict and all(key in transition for key in
                 ("name", "pre", "post")), "invalid transition fields")
        _require(type(transition["name"]) is str, "invalid transition name")
        for side in ("pre", "post"):
            arcs = transition[side]
            _require(type(arcs) is list, "invalid arc list")
            seen = set()
            for arc in arcs:
                tick()
                _require(type(arc) is list and len(arc) == 2 and
                         _integer(arc[0], 0, n) and _integer(arc[1], 1, 2**64),
                         "invalid weighted arc")
                _require(arc[0] not in seen, "duplicate arc place")
                seen.add(arc[0])
    _require(type(problem["target"]) is list, "invalid target list")
    for row in problem["target"]:
        tick()
        _require(type(row) is dict and all(key in row for key in
                 ("coefficients", "bound", "equality")), "invalid target fields")
        coefficients = row["coefficients"]
        _require(type(coefficients) is list and len(coefficients) == n,
                 "invalid target dimension")
        for coefficient in coefficients:
            tick()
            _require(_integer(coefficient, -(2**63), 2**63), "invalid target coefficient")
        _require(_integer(row["bound"], -(2**63), 2**63), "invalid target bound")
        _require(type(row["equality"]) is bool, "invalid target equality")
    return n


def _unsatisfiable(clauses, tick):
    """Kosaraju SCCs on 2-CNF plus the allowed threshold semantic axioms."""
    atoms = {}
    encoded = []
    for clause in clauses:
        tick()
        literals = []
        for form, threshold, negated in clause:
            atom = (form, threshold)
            if atom not in atoms:
                atoms[atom] = len(atoms)
            literals.append(2 * atoms[atom] + int(negated))
        encoded.append(literals)
    graph = [[] for _ in range(2 * len(atoms))]
    reverse = [[] for _ in graph]

    def edge(source, target):
        graph[source].append(target)
        reverse[target].append(source)

    for clause in encoded:
        tick()
        a, b = clause[0], clause[-1]
        edge(a ^ 1, b)
        edge(b ^ 1, a)
    thresholds = {}
    for (form, threshold), atom in atoms.items():
        tick()
        thresholds.setdefault(form, []).append((threshold, 2 * atom))
        if threshold <= 0 and all(coefficient >= 0 for _, coefficient in form):
            edge(2 * atom + 1, 2 * atom)
        if threshold > 0 and all(coefficient <= 0 for _, coefficient in form):
            edge(2 * atom, 2 * atom + 1)
    for ordered in thresholds.values():
        tick()
        ordered.sort()
        for (_, lower), (_, higher) in zip(ordered, ordered[1:]):
            tick()
            edge(higher, lower)
            edge(lower ^ 1, higher ^ 1)
    seen = set()
    finish = []
    for start in range(len(graph)):
        tick()
        if start in seen:
            continue
        seen.add(start)
        stack = [(start, iter(graph[start]))]
        while stack:
            tick()
            vertex, outgoing = stack[-1]
            successor = next(outgoing, None)
            if successor is None:
                finish.append(vertex)
                stack.pop()
            elif successor not in seen:
                seen.add(successor)
                stack.append((successor, iter(graph[successor])))
    component = [-1] * len(graph)
    for start in reversed(finish):
        tick()
        if component[start] != -1:
            continue
        component[start] = start
        stack = [start]
        while stack:
            tick()
            vertex = stack.pop()
            for successor in reverse[vertex]:
                tick()
                if component[successor] == -1:
                    component[successor] = start
                    stack.append(successor)
    return any(component[2 * atom] == component[2 * atom + 1]
               for atom in range(len(atoms)))


def verify_signed_threshold(problem, proof, deadline=None):
    def tick():
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("signed threshold checker deadline")

    tick()
    n = _validate_problem(problem, tick)
    _require(type(proof) is dict and set(proof) == {"kind", "forms", "clauses"},
             "invalid signed threshold proof fields")
    _require(proof["kind"] == "signed-threshold-invariant-v1", "wrong proof kind")
    _require(type(proof["forms"]) is list, "invalid form list")
    forms = []
    for raw_form in proof["forms"]:
        tick()
        _require(type(raw_form) is list, "invalid sparse form")
        form = []
        previous = -1
        for term in raw_form:
            tick()
            _require(type(term) is list and len(term) == 2 and
                     _integer(term[0], 0, n), "invalid sparse term")
            place, coefficient = term[0], _decimal(term[1], tick)
            _require(place > previous and coefficient != 0,
                     "noncanonical sparse form")
            previous = place
            form.append((place, coefficient))
        forms.append(tuple(form))
    _require(type(proof["clauses"]) is list, "invalid clause list")
    invariant = []
    for raw_clause in proof["clauses"]:
        tick()
        _require(type(raw_clause) is list and 1 <= len(raw_clause) <= 2,
                 "expected unary or binary clause")
        clause = []
        for literal in raw_clause:
            _require(type(literal) is dict and set(literal) ==
                     {"form", "threshold", "negated"}, "invalid literal fields")
            _require(_integer(literal["form"], 0, len(forms)) and
                     type(literal["negated"]) is bool, "invalid literal reference")
            clause.append((forms[literal["form"]], _decimal(literal["threshold"], tick),
                           literal["negated"]))
        invariant.append(clause)
    for clause in invariant:
        tick()
        satisfied = False
        for form, threshold, negated in clause:
            value = 0
            for place, coefficient in form:
                tick()
                value += coefficient * problem["initial"][place]
            satisfied |= (value >= threshold) != negated
        _require(satisfied, "initial marking violates invariant")
    for transition_index, transition in enumerate(problem["transitions"]):
        tick()
        delta = {}
        guards = []
        for place, weight in transition["pre"]:
            tick()
            guards.append([(((place, 1),), weight, False)])
            delta[place] = -weight
        for place, weight in transition["post"]:
            tick()
            delta[place] = delta.get(place, 0) + weight
        for clause_index, clause in enumerate(invariant):
            tick()
            negated_successor = []
            for form, threshold, negated in clause:
                change = 0
                for place, coefficient in form:
                    tick()
                    change += coefficient * delta.get(place, 0)
                negated_successor.append([(form, threshold - change, not negated)])
            _require(_unsatisfiable(invariant + guards + negated_successor, tick),
                     f"invariant not inductive at transition {transition_index}, clause {clause_index}")
    target = []
    for row in problem["target"]:
        tick()
        form = tuple((place, coefficient) for place, coefficient in
                     enumerate(row["coefficients"]) if coefficient)
        target.append([(form, row["bound"], False)])
        if row["equality"]:
            target.append([(form, row["bound"] + 1, True)])
    _require(_unsatisfiable(invariant + target, tick), "invariant does not exclude target")
    tick()
    return "python-signed-threshold-invariant"
