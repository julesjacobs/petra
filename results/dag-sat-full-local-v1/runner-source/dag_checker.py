"""Independent original-net encoding and RUP checker for acyclic controllers.

Conserved one-hot control and acyclicity make every execution a finite path.
Flow clauses select a path prefix; conditional updates in topological order
preserve every original guard and counter value. Bit widths use upper bounds
from all positive edge effects. RUP contradiction therefore excludes every
original execution satisfying the final signed linear constraints.
"""
import math
import time
from dataclasses import dataclass


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Budget:
    def __init__(self, deadline, max_work):
        require(type(deadline) in (int, float) and math.isfinite(deadline), "invalid deadline")
        require(type(max_work) is int and max_work >= 0, "invalid work limit")
        self.deadline = deadline
        self.remaining = max_work

    def tick(self, amount=1):
        self.remaining -= amount
        if self.remaining < 0:
            raise TimeoutError("DAG verification work limit")
        if time.monotonic() >= self.deadline:
            raise TimeoutError("DAG verification deadline")


@dataclass
class Encoding:
    variables: int
    clauses: list
    choices: list


def validate(problem, budget):
    require(type(problem) is dict, "invalid original problem")
    require(all(key in problem for key in ("places", "initial", "transitions", "target")), "missing original problem fields")
    require(type(problem["places"]) is list and all(type(p) is str for p in problem["places"]), "invalid places")
    n = len(problem["places"])
    initial = problem["initial"]
    require(type(initial) is list and len(initial) == n, "initial dimension mismatch")
    for value in initial:
        budget.tick()
        require(type(value) is int and 0 <= value < 2**64, "invalid initial marking")
    require(type(problem["transitions"]) is list, "invalid transitions")
    for tr in problem["transitions"]:
        budget.tick()
        require(type(tr) is dict and all(key in tr for key in ("name", "pre", "post")), "invalid transition")
        require(type(tr["name"]) is str, "invalid transition name")
        for field in ("pre", "post"):
            require(type(tr[field]) is list, "invalid arcs")
            seen = set()
            for term in tr[field]:
                budget.tick()
                require(type(term) is list and len(term) == 2, "invalid arc")
                p, w = term
                require(type(p) is int and 0 <= p < n and p not in seen, "invalid or duplicate arc place")
                require(type(w) is int and 0 < w < 2**64, "invalid arc weight")
                seen.add(p)
    require(type(problem["target"]) is list, "invalid target")
    for c in problem["target"]:
        budget.tick()
        require(type(c) is dict and all(key in c for key in ("coefficients", "bound", "equality")), "invalid constraint")
        require(type(c["coefficients"]) is list and len(c["coefficients"]) == n, "target dimension mismatch")
        require(type(c["equality"]) is bool, "invalid equality flag")
        for value in c["coefficients"] + [c["bound"]]:
            budget.tick()
            require(type(value) is int and -2**63 <= value < 2**63, "invalid signed target coefficient")


class Rup:
    def __init__(self, variables, clauses, budget):
        self.variables = variables
        self.budget = budget
        budget.tick(variables + 1)
        self.clauses = []
        self.watches = {}
        self.units = []
        self.empty = False
        for clause in clauses:
            self.add(clause)

    def normalize(self, clause):
        self.budget.tick()
        require(type(clause) is list, "invalid RUP clause")
        seen = set()
        result = []
        for lit in clause:
            self.budget.tick()
            require(type(lit) is int and 0 < abs(lit) <= self.variables, "invalid RUP literal")
            if lit not in seen:
                seen.add(lit)
                result.append(lit)
        return result

    def add(self, clause):
        clause = self.normalize(clause)
        literals = set(clause)
        self.budget.tick(len(clause))
        if any(-lit in literals for lit in clause):
            return
        index = len(self.clauses)
        self.clauses.append(clause)
        if len(clause) == 0:
            self.empty = True
        elif len(clause) == 1:
            self.units.append(clause[0])
        else:
            self.watches.setdefault(clause[0], []).append(index)
            self.watches.setdefault(clause[1], []).append(index)

    def implied(self, clause):
        clause = self.normalize(clause)
        if self.empty:
            return True
        values = {}
        queue = []

        def assign(lit):
            self.budget.tick()
            old = values.get(abs(lit))
            if old is not None:
                return old == (lit > 0)
            values[abs(lit)] = lit > 0
            queue.append(lit)
            return True

        def value(lit):
            v = values.get(abs(lit))
            return None if v is None else v == (lit > 0)

        for lit in clause:
            if not assign(-lit):
                return True
        for lit in self.units:
            if not assign(lit):
                return True
        cursor = 0
        while cursor < len(queue):
            self.budget.tick()
            false = -queue[cursor]
            cursor += 1
            watching = self.watches.get(false, [])
            i = 0
            while i < len(watching):
                self.budget.tick()
                index = watching[i]
                c = self.clauses[index]
                if c[0] == false:
                    c[0], c[1] = c[1], c[0]
                require(c[1] == false, "corrupt internal watch")
                if value(c[0]) is True:
                    i += 1
                    continue
                replacement = None
                for j in range(2, len(c)):
                    self.budget.tick()
                    if value(c[j]) is not False:
                        replacement = j
                        break
                if replacement is not None:
                    c[1], c[replacement] = c[replacement], c[1]
                    watching[i] = watching[-1]
                    watching.pop()
                    self.watches.setdefault(c[1], []).append(index)
                else:
                    if not assign(c[0]):
                        return True
                    i += 1
        return False


def verify_rup(encoding, additions, budget):
    require(type(additions) is list and additions and additions[-1] == [], "RUP proof must end with an empty clause")
    checker = Rup(encoding.variables, encoding.clauses, budget)
    for clause in additions:
        budget.tick()
        require(checker.implied(clause), "clause is not RUP")
        checker.add(clause)
    budget.tick()
    return "python-dag-cnf-rup"


class Cnf:
    def __init__(self, budget):
        self.budget = budget
        self.variables = 1
        self.clauses = [[1]]
        self.ands = {}
        self.xors = {}

    def variable(self):
        self.budget.tick()
        self.variables += 1
        require(self.variables < 2**31, "CNF variable overflow")
        return self.variables

    def clause(self, literals):
        self.budget.tick(len(literals) + 1)
        self.clauses.append(literals)

    def and_(self, a, b):
        self.budget.tick()
        a, b = sorted((a, b))
        if a == -1 or b == -1 or a == -b:
            return -1
        if a == 1:
            return b
        if b == 1 or a == b:
            return a
        key = (a, b)
        if key not in self.ands:
            z = self.variable()
            self.clause([-z, a])
            self.clause([-z, b])
            self.clause([z, -a, -b])
            self.ands[key] = z
        return self.ands[key]

    def xor(self, a, b):
        self.budget.tick()
        a, b = sorted((a, b))
        if a == b:
            return -1
        if a == -b:
            return 1
        if a == -1:
            return b
        if b == -1:
            return a
        if a == 1:
            return -b
        if b == 1:
            return -a
        key = (a, b)
        if key not in self.xors:
            z = self.variable()
            self.clause([-a, -b, -z])
            self.clause([a, b, -z])
            self.clause([a, -b, z])
            self.clause([-a, b, z])
            self.xors[key] = z
        return self.xors[key]

    def or_(self, a, b):
        return -self.and_(-a, -b)

    def mux(self, s, t, f):
        self.budget.tick()
        if s == 1:
            return t
        if s == -1:
            return f
        if t == f:
            return t
        return self.or_(self.and_(s, t), self.and_(-s, f))

    def add(self, a, b):
        carry = -1
        result = []
        for av, bv in zip(a, b):
            self.budget.tick()
            x = self.xor(av, bv)
            result.append(self.xor(x, carry))
            carry = self.or_(self.and_(av, bv), self.and_(x, carry))
        return result

    def ge(self, a, b):
        result = 1
        for av, bv in zip(a, b):
            self.budget.tick()
            result = self.or_(self.and_(av, -bv), self.and_(-self.xor(av, bv), result))
        return result


def constant(value, width):
    return [1 if value & (1 << i) else -1 for i in range(width)]


def _encode(problem, control_places, budget):
    import heapq

    budget.tick()
    validate(problem, budget)
    n = len(problem['places'])
    require(type(control_places) is list and control_places, 'empty or invalid control projection')
    previous = -1
    for p in control_places:
        budget.tick()
        require(type(p) is int and previous < p < n, 'invalid or unsorted control place')
        previous = p
    selected = set(control_places)
    require(sum(problem['initial'][p] for p in selected) == 1, 'control requires exactly one initial token')
    initial = next(p for p in control_places if problem['initial'][p] == 1)
    outgoing = {p: [] for p in control_places}
    for tid, tr in enumerate(problem['transitions']):
        budget.tick()
        pre = [(p, w) for p, w in tr['pre'] if p in selected]
        post = [(p, w) for p, w in tr['post'] if p in selected]
        consumed = sum(w for _, w in pre)
        require(consumed == sum(w for _, w in post), 'control token conservation fails')
        require(consumed != 0, 'reachable control graph stutters')
        if consumed == 1:
            outgoing[pre[0][0]].append((tid, post[0][0]))
    reachable = {initial}
    pending = [initial]
    for source in pending:
        budget.tick()
        for tid, target in outgoing[source]:
            budget.tick()
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    incoming = {p: [] for p in reachable}
    for source in reachable:
        for tid, target in outgoing[source]:
            budget.tick()
            incoming[target].append((tid, source))
    degree = {p: len(edges) for p, edges in incoming.items()}
    ready = [p for p in reachable if degree[p] == 0]
    heapq.heapify(ready)
    topological = []
    while ready:
        budget.tick()
        source = heapq.heappop(ready)
        topological.append(source)
        for _, target in outgoing[source]:
            degree[target] -= 1
            if degree[target] == 0:
                heapq.heappush(ready, target)
    require(len(topological) == len(reachable), 'reachable control graph is cyclic')
    ordered = [(source, tid, target) for source in topological for tid, target in sorted(outgoing[source])]
    b = Cnf(budget)
    choices = [(tid, b.variable()) for _, tid, _ in ordered]
    literal_of = dict(choices)
    for source in topological:
        ins = sorted(literal_of[tid] for tid, _ in incoming[source])
        outs = [literal_of[tid] for tid, _ in sorted(outgoing[source])]
        for values in (ins, outs):
            for i, a in enumerate(values):
                for c in values[i+1:]:
                    b.clause([-a, -c])
        if source != initial:
            for lit in outs:
                b.clause([-lit] + ins)
    upper = list(problem['initial'])
    effects = []
    for _, tid, _ in ordered:
        budget.tick()
        delta = {}
        for field, sign in (('pre', -1), ('post', 1)):
            for p, w in problem['transitions'][tid][field]:
                budget.tick()
                delta[p] = delta.get(p, 0) + sign*w
        delta = {p: w for p, w in sorted(delta.items()) if w}
        for p, w in delta.items():
            if w > 0:
                upper[p] += w
        effects.append(delta)
    for place in control_places:
        upper[place] = 1

    def const(value, width):
        budget.tick(width)
        return constant(value, width)

    markings = [const(value, max(1, upper[p].bit_length())) for p, value in enumerate(problem['initial'])]
    for (_, tid, _), delta in zip(ordered, effects):
        budget.tick()
        literal = literal_of[tid]
        for p, weight in sorted(problem['transitions'][tid]['pre']):
            if weight > upper[p]:
                b.clause([-literal])
            else:
                enabled = b.ge(markings[p], const(weight, len(markings[p])))
                b.clause([-literal, enabled])
        for p, d in delta.items():
            width = len(markings[p])
            updated = b.add(markings[p], const(d % (1 << width), width))
            markings[p] = [b.mux(literal, new, old) for new, old in zip(updated, markings[p])]
    for constraint in problem['target']:
        budget.tick()
        coefficients = constraint['coefficients']
        left_constant = max(-constraint['bound'], 0)
        right_constant = max(constraint['bound'], 0)
        left_bound = left_constant + sum(c*u for c, u in zip(coefficients, upper) if c > 0)
        right_bound = right_constant + sum(-c*u for c, u in zip(coefficients, upper) if c < 0)
        width = max(1, max(left_bound, right_bound).bit_length())
        left = const(left_constant, width)
        right = const(right_constant, width)
        for p, coefficient in enumerate(coefficients):
            budget.tick()
            if not coefficient:
                continue
            term = const(0, width)
            for shift in range(64):
                if abs(coefficient) & (1 << shift):
                    shifted = const(0, width)
                    for i, bit in enumerate(markings[p]):
                        if i + shift < width:
                            shifted[i+shift] = bit
                    term = b.add(term, shifted)
            if coefficient > 0:
                left = b.add(left, term)
            else:
                right = b.add(right, term)
        if constraint['equality']:
            for a, c in zip(left, right):
                b.clause([-a, c])
                b.clause([a, -c])
        else:
            b.clause([b.ge(left, right)])
    budget.tick()
    return Encoding(b.variables, b.clauses, choices)


def encode(problem, control_places, deadline=None, max_work=20_000_000):
    if deadline is None:
        deadline = time.monotonic() + 60
    return _encode(problem, control_places, Budget(deadline, max_work))


def verify(problem, proof, deadline=None, max_work=20_000_000):
    if deadline is None:
        deadline = time.monotonic() + 60
    budget = Budget(deadline, max_work)
    budget.tick()
    require(type(proof) is dict and set(proof) == {'kind', 'control_places', 'additions'}, 'invalid DAG proof fields')
    require(proof['kind'] == 'dag-cnf-rup-v1', 'invalid DAG proof kind')
    encoding = _encode(problem, proof['control_places'], budget)
    return verify_rup(encoding, proof['additions'], budget)
