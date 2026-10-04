"""Independent exact checker for controller-indexed serial-component invariants."""
import math
import time


def verify(q, cert, deadline, max_obligations=1_000_000):
    from raw_stress_worker import U64_MAX, validate

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(type(deadline) in (int, float) and math.isfinite(deadline), "invalid deadline")
    require(type(max_obligations) is int and max_obligations >= 0, "invalid work limit")
    work = 0

    def tick():
        nonlocal work
        work += 1
        if time.monotonic() >= deadline:
            raise TimeoutError("raw invariant verification deadline")
        if work > max_obligations:
            raise TimeoutError("raw invariant verification work limit")

    def fields(value, expected):
        tick()
        require(type(value) is dict and set(value) == set(expected.split()), "invalid certificate fields")

    def index(value, size):
        tick()
        require(type(value) is int and 0 <= value < size, "invalid certificate index")
        return value

    def vector(value, size):
        tick()
        require(type(value) is list and len(value) == size, "coefficient/control dimension mismatch")
        for x in value:
            tick()
            require(type(x) is int and 0 <= x <= U64_MAX, "invalid u64 coefficient/control value")
        return value

    def sparse_add(out, values, scale=1):
        for p, w in values.items():
            tick()
            value = out.get(p, 0) + scale * w
            if value:
                out[p] = value
            else:
                out.pop(p, None)

    def linear(base, periods, coefficients):
        result = {}
        sparse_add(result, base)
        require(type(coefficients) is list, "coefficients must be a sparse list")
        previous = -1
        for term in coefficients:
            tick()
            require(type(term) is list and len(term) == 2, "invalid sparse coefficient term")
            p, coefficient = term
            index(p, len(periods))
            require(p > previous, "coefficient indices must be sorted and unique")
            require(type(coefficient) is int and 0 < coefficient <= U64_MAX, "invalid u64 coefficient")
            sparse_add(result, periods[p], coefficient)
            previous = p
        return result

    tick()
    try:
        validate(q)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError(f"invalid original raw query: {error}") from error
    tick()
    fields(cert, "format control_places credits initial_node initial_coefficients nodes")
    require(cert["format"] == "raw-component-invariant-v1", "unsupported invariant format")
    n = len(q["places"])
    selected = cert["control_places"]
    require(type(selected) is list, "control places must be a list")
    previous = -1
    positions = {}
    for p in selected:
        index(p, n)
        require(p > previous, "control places must be sorted and unique")
        positions[p] = len(positions)
        previous = p
    zero = set(q["target"]["zero_places"])
    responses = set(q["target"]["response_places"])
    columns = {}
    for p in responses:
        tick()
        columns[p] = {p: 1}
    require(type(cert["credits"]) is list, "credits must be a list")
    for credit in cert["credits"]:
        fields(credit, "place terms")
        p = index(credit["place"], n)
        require(p in zero and p not in columns, "credit place must be a unique completion-zero place")
        terms = credit["terms"]
        require(type(terms) is list, "credit terms must be a list")
        column = {}
        for term in terms:
            tick()
            require(type(term) is list and len(term) == 2, "invalid credit term")
            response, weight = term
            index(response, n)
            require(response in responses and response not in column, "invalid or repeated credit response")
            require(type(weight) is int and 0 < weight <= U64_MAX, "invalid credit weight")
            column[response] = weight
        columns[p] = column

    components = []
    for component in q["target"]["excluded_semilinear"]:
        tick()
        base = {}
        for p, weight in component["base"]:
            tick()
            base[p] = weight
        periods = []
        for period in component["periods"]:
            tick()
            values = {}
            for p, weight in period:
                tick()
                values[p] = weight
            periods.append(values)
        components.append((base, periods))

    transitions = []
    for transition_id, transition in enumerate(q["transitions"]):
        tick()
        pre, delta, effect = {}, {}, {}
        for field, sign in (("pre", -1), ("post", 1)):
            for p, weight in transition[field]:
                tick()
                if p in positions:
                    if field == "pre":
                        pre[positions[p]] = weight
                    sparse_add(delta, {positions[p]: weight}, sign)
                sparse_add(effect, columns.get(p, {}), sign * weight)
        if delta or effect:
            transitions.append((transition_id, pre, delta, effect))

    sources = []
    anchored = {}
    readers = {}
    for _, pre, _, _ in transitions:
        for p in pre:
            tick()
            readers[p] = readers.get(p, 0) + 1
    for transition in transitions:
        tick()
        pre = transition[1]
        if not pre:
            sources.append(transition)
        else:
            p = min(pre, key=lambda p: (readers[p], p))
            anchored.setdefault(p, []).append(transition)

    def candidates(control):
        yield from sources
        for p, bucket in anchored.items():
            tick()
            if control[p]:
                for transition in bucket:
                    tick()
                    if control[p] >= transition[1][p]:
                        yield transition

    nodes = cert["nodes"]
    require(type(nodes) is list and nodes, "invariant nodes must be a nonempty list")
    seen = set()
    for node in nodes:
        fields(node, "control component edges")
        vector(node["control"], len(selected))
        index(node["component"], len(components))
        key = (tuple(node["control"]), node["component"])
        require(key not in seen, "duplicate invariant node")
        seen.add(key)

    initial = nodes[index(cert["initial_node"], len(nodes))]
    for i, p in enumerate(selected):
        tick()
        require(initial["control"][i] == q["initial"][p], "initial controller mismatch")
    credited_initial = {}
    for p, column in columns.items():
        tick()
        sparse_add(credited_initial, column, q["initial"][p])
    base, periods = components[initial["component"]]
    require(credited_initial == linear(base, periods, cert["initial_coefficients"]), "initial affine membership mismatch")

    for node in nodes:
        tick()
        control = node["control"]
        source_base, source_periods = components[node["component"]]
        require(type(node["edges"]) is list, "edges must be a list")
        edges = {}
        for edge in node["edges"]:
            fields(edge, "transition target base_coefficients period_coefficients")
            t = index(edge["transition"], len(q["transitions"]))
            require(t not in edges, "duplicate transition edge")
            index(edge["target"], len(nodes))
            edges[t] = edge
        for t, pre, delta, effect in candidates(control):
            tick()
            enabled = True
            for p, weight in pre.items():
                tick()
                enabled &= control[p] >= weight
            if not enabled:
                continue
            require(t in edges, "missing enabled transition edge")
            edge = edges.pop(t)
            successor = control[:]
            for p, change in delta.items():
                tick()
                successor[p] += change
                require(0 <= successor[p] <= U64_MAX, "projected control overflow")
            destination = nodes[edge["target"]]
            require(successor == destination["control"], "projected successor mismatch")
            target_base, target_periods = components[destination["component"]]
            shifted = {}
            sparse_add(shifted, source_base)
            sparse_add(shifted, effect)
            require(shifted == linear(target_base, target_periods, edge["base_coefficients"]), "affine base mapping mismatch")
            maps = edge["period_coefficients"]
            require(type(maps) is list and len(maps) == len(source_periods), "period mapping dimension mismatch")
            for period, coefficients in zip(source_periods, maps):
                tick()
                require(period == linear({}, target_periods, coefficients), "affine period mapping mismatch")
        require(not edges, "extra disabled or stuttering transition edge")
    tick()
    return "python-raw-component-invariant"
