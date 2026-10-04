"""Independent inductive checking of phase-partitioned pair relations."""
import time


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_phase_pair(problem, proof, deadline=None):
    def tick():
        require(deadline is None or time.monotonic() < deadline, 'phase pair checker deadline')
    def integer(x, lo, hi):
        return type(x) is int and lo <= x < hi
    def bits(value):
        while value:
            bit = value & -value
            yield bit.bit_length() - 1
            value -= bit
    n = len(problem['places'])
    require(len(problem['initial']) == n and all(integer(m, 0, 2**64) for m in problem['initial']), 'invalid initial marking')
    require(type(proof) is dict and set(proof) == {'kind', 'groups', 'landmarks', 'relations', 'conflicts'}, 'invalid phase pair proof fields')
    require(proof['kind'] == 'phase-pair-closure-v1', 'wrong phase pair kind')
    owner = [None] * n
    require(type(proof['groups']) is list, 'invalid group list')
    for group_id, group in enumerate(proof['groups']):
        tick()
        require(type(group) is list and group and all(integer(i, 0, n) for i in group), 'invalid group places')
        require(group == sorted(set(group)), 'unordered or duplicate group places')
        require(sum(problem['initial'][i] for i in group) <= 1, 'initial group mass exceeds one')
        for i in group:
            require(owner[i] is None, 'overlapping groups')
            owner[i] = group_id
    require(all(g is not None for g in owner), 'missing group places')
    transitions = []
    for t in problem['transitions']:
        tick()
        sides = []
        for side in ('pre', 'post'):
            arcs = t[side]
            require(type(arcs) is list, 'invalid arcs')
            require(all(type(a) in (list, tuple) and len(a) == 2 and integer(a[0], 0, n) and integer(a[1], 1, 2**64) for a in arcs), 'invalid weighted arc')
            require(len({i for i, _ in arcs}) == len(arcs), 'duplicate arc place')
            sides.append(dict(arcs))
        pre, post = sides
        mass = {}
        for sign, arcs in ((-1, pre), (1, post)):
            for i, weight in arcs.items():
                mass[owner[i]] = mass.get(owner[i], 0) + sign * weight
        require(all(delta <= 0 for delta in mass.values()), 'group mass increases')
        transitions.append((pre, post))
    landmarks = proof['landmarks']
    require(type(landmarks) is list and all(integer(t, 0, len(transitions)) for t in landmarks), 'invalid landmark')
    require(landmarks == sorted(set(landmarks)), 'unordered landmarks')
    landmarks = set(landmarks)
    words = (n + 63) // 64
    require(2 * n * words <= 8_000_000, 'relation size limit')
    require(type(proof['relations']) is list and len(proof['relations']) == 2, 'expected two relations')
    relations, live = [], []
    for matrix in proof['relations']:
        require(type(matrix) is list and len(matrix) == n, 'invalid matrix height')
        rows = []
        for encoded in matrix:
            tick()
            require(type(encoded) is list and len(encoded) == words and all(integer(w, 0, 2**64) for w in encoded), 'invalid row words')
            row = sum(word << (64 * index) for index, word in enumerate(encoded))
            require(row >> n == 0, 'nonzero row padding')
            rows.append(row)
        diagonal = sum(1 << i for i, row in enumerate(rows) if row & (1 << i))
        for i, row in enumerate(rows):
            tick()
            require(not row or diagonal & (1 << i), 'pair without source diagonal')
            require(row & ~diagonal == 0, 'pair without target diagonal')
            require(all(rows[j] & (1 << i) for j in bits(row)), 'asymmetric relation')
        relations.append(rows)
        live.append(diagonal)
    initial = sum(1 << i for i, m in enumerate(problem['initial']) if m)
    for i in bits(initial):
        require(initial & ~relations[0][i] == 0, 'initial pair missing')
    for phase in (0, 1):
        for tid, (pre, post) in enumerate(transitions):
            tick()
            if any(w > 1 for w in (*pre.values(), *post.values())):
                continue
            if any(not live[phase] & (1 << i) for i in pre):
                continue
            if any(not relations[phase][i] & (1 << j) for i in pre for j in pre):
                continue
            surviving = live[phase]
            for i in pre:
                surviving &= relations[phase][i]
            for i in pre.keys() - post.keys():
                surviving &= ~(1 << i)
            dest = 1 if phase == 1 or tid in landmarks else 0
            if phase != dest:
                for i in bits(surviving):
                    require((relations[phase][i] & surviving) & ~relations[dest][i] == 0, 'preserved pair omitted across phase change')
            produced = sum(1 << i for i in post)
            for i in post:
                require((surviving | produced) & ~relations[dest][i] == 0, 'post pair missing')
    def required(claim):
        require(type(claim) is dict and set(claim) == {'place', 'constraint', 'negated'}, 'invalid required-place claim')
        i, c, negate = claim['place'], claim['constraint'], claim['negated']
        require(integer(i, 0, n) and integer(c, 0, len(problem['target'])) and type(negate) is bool, 'invalid target references')
        row = problem['target'][c]
        require(type(row['equality']) is bool and (not negate or row['equality']), 'invalid target direction')
        require(len(row['coefficients']) == n and all(integer(a, -(2**63), 2**63) for a in row['coefficients']) and integer(row['bound'], -(2**63), 2**63), 'invalid target arithmetic')
        sign = -1 if negate else 1
        require(sign * row['coefficients'][i] > 0, 'required place coefficient is not positive')
        upper = sum(max(0, sign * a) for j, a in enumerate(row['coefficients']) if j != i)
        require(upper < sign * row['bound'], 'target does not require place')
        return i
    require(type(proof['conflicts']) is list and len(proof['conflicts']) == 2, 'expected two conflicts')
    for phase, conflict in enumerate(proof['conflicts']):
        require(type(conflict) is dict and set(conflict) == {'left', 'right'}, 'invalid conflict')
        a, b = required(conflict['left']), required(conflict['right'])
        require(not relations[phase][a] & (1 << b), 'target pair is present')
    tick()
    return 'python-phase-pair-closure'
