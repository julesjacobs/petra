#!/usr/bin/env python3
"""Sequential cold-process backend timings on byte-identical artifact queries."""
from kreach_adapter import mist
import argparse, collections, copy, itertools, math, fractions, hashlib, json, os, pathlib, platform, re, signal, subprocess, time, threading
ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(command, cwd, seconds, output):
    start = time.perf_counter()
    with output.open('w') as f:
        process = subprocess.Popen(command, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        expired = threading.Event()
        def kill():
            try:
                os.killpg(process.pid, signal.SIGKILL)
                expired.set()
            except ProcessLookupError:
                pass
        timer = threading.Timer(seconds, kill)
        timer.start()
        process.wait()
        timer.cancel()
        timed_out = expired.is_set()
    return time.perf_counter()-start, process.returncode, timed_out

def original_rows(problem):
    n = len(problem['transitions'])
    delta = [[0]*n for _ in problem['places']]
    for t, tr in enumerate(problem['transitions']):
        for p,w in tr['pre']: delta[p][t] -= w
        for p,w in tr['post']: delta[p][t] += w
    rows = []
    for t in range(n):
        a = [0]*n; a[t] = 1; rows.append((a,0))
    rows += [(a,-m) for a,m in zip(delta,problem['initial'])]
    for c in problem['target']:
        a = [sum(x*d[t] for x,d in zip(c['coefficients'],delta)) for t in range(n)]
        b = c['bound'] - sum(x*m for x,m in zip(c['coefficients'],problem['initial']))
        rows.append((a,b))
        if c['equality']: rows.append(([-x for x in a],-b))
    return rows

def verify_threshold_closure(problem, proof):
    dimensions = len(problem['places'])
    thresholds = proof['thresholds']
    assert len(thresholds) == dimensions
    assert all(type(k) is int and 0 <= k < 2**64 for k in thresholds)
    states = set()
    for state in proof['states']:
        assert len(state) == dimensions
        assert all(type(x) is int and 0 <= x <= k for x,k in zip(state,thresholds))
        states.add(tuple(state))
    assert tuple(min(x,k) for x,k in zip(problem['initial'],thresholds)) in states
    transitions = []
    for transition in problem['transitions']:
        pre, post = [0]*dimensions, [0]*dimensions
        for p,w in transition['pre']: pre[p] += w
        for p,w in transition['post']: post[p] += w
        transitions.append((pre,post))
    for state in states:
        target_possible = True
        for constraint in problem['target']:
            lower = upper = sum(a*x for a,x in zip(constraint['coefficients'],state))
            lower_infinite = upper_infinite = False
            for a,x,k in zip(constraint['coefficients'],state,thresholds):
                if x == k:
                    lower_infinite |= a < 0
                    upper_infinite |= a > 0
            bound = constraint['bound']
            possible = upper_infinite or upper >= bound
            if constraint['equality']:
                possible &= lower_infinite or lower <= bound
            target_possible &= possible
        assert not target_possible
        for pre,post in transitions:
            successors = []
            for x,k,a,b in zip(state,thresholds,pre,post):
                if x < k:
                    if x < a: break
                    successors.append((min(x-a+b,k),))
                else:
                    lower = max(k,a)-a+b
                    successors.append(range(min(lower,k),k+1))
            else:
                assert all(successor in states for successor in itertools.product(*successors))
    return 'python-threshold-closure'

def verify_causal_state_equation(problem, proof):
    assert set(proof) == {'kind', 'root'}
    n = len(problem['places'])
    transitions = problem['transitions']
    base = [(i, None, 1) for i in range(n)]
    for constraint in problem['target']:
        if constraint['equality']: base.append((None, constraint, -1))
        base.append((None, constraint, 1))
    pending = [(proof['root'], ())]
    while pending:
        node, ancestors = pending.pop()
        if node['rule'] == 'support':
            assert set(node) == {'rule', 'places', 'blocked', 'omit', 'enter'}
            places, blocked = node['places'], node['blocked']
            assert places == sorted(set(places))
            assert all(type(p) is int and 0 <= p < n for p in places)
            chosen = set(places)
            assert all(m == 0 or p in chosen for p, m in enumerate(problem['initial']))
            assert type(blocked) is int and 0 <= blocked < len(transitions)
            assert any(p not in chosen for p, w in transitions[blocked]['pre'])
            frontier = {t: 1 for t, transition in enumerate(transitions)
                        if all(p in chosen for p, w in transition['pre'])
                        and any(p not in chosen for p, w in transition['post'])}
            pending.append((node['enter'], ancestors + ((frontier, 1),)))
            pending.append((node['omit'], ancestors + (({blocked: -1}, 0),)))
            continue
        assert node['rule'] == 'farkas' and set(node) == {'rule', 'multipliers'}
        place_weights = [fractions.Fraction(0) for _ in range(n)]
        transition_weights = collections.defaultdict(fractions.Fraction)
        rhs = fractions.Fraction(0)
        previous = -1
        for index, raw in node['multipliers']:
            assert type(index) is int and previous < index < len(base) + len(ancestors)
            assert type(raw) is str
            previous = index
            weight = fractions.Fraction(raw)
            assert weight > 0
            if index >= len(base):
                coefficients, bound = ancestors[index - len(base)]
                rhs += weight * bound
                for t, coefficient in coefficients.items(): transition_weights[t] += weight * coefficient
            else:
                place, constraint, sign = base[index]
                if place is not None:
                    place_weights[place] += weight
                    rhs -= weight * problem['initial'][place]
                else:
                    weight *= sign
                    rhs += weight * (constraint['bound'] - sum(a*m for a, m in zip(constraint['coefficients'], problem['initial'])))
                    for p, coefficient in enumerate(constraint['coefficients']): place_weights[p] += weight * coefficient
        assert rhs > 0
        for t, transition in enumerate(transitions):
            lhs = transition_weights[t]
            lhs += sum(place_weights[p]*w for p, w in transition['post'])
            lhs -= sum(place_weights[p]*w for p, w in transition['pre'])
            assert lhs <= 0
    return 'python-causal-state-equation'

def verify_proof(problem, proof):
    kind = proof['kind']
    if kind == 'token-cut-v1':
        from token_cut_checker import verify_token_cut
        return verify_token_cut(problem, proof)
    if kind == 'token-moment-v1':
        from token_moment_checker import verify_token_moment
        return verify_token_moment(problem, proof)
    if kind == 'causal-state-equation-v1':
        return verify_causal_state_equation(problem, proof)
    if kind == 'sparse-farkas-v1':
        n = len(problem['places'])
        rows = [(i, None, 1) for i in range(n)]
        for c in problem['target']:
            if c['equality']: rows.append((None, c, -1))
            rows.append((None, c, 1))
        coefficients = [fractions.Fraction(0) for _ in range(n)]
        rhs = fractions.Fraction(0)
        previous = -1
        for index, raw in proof['multipliers']:
            assert type(index) is int and previous < index < len(rows)
            previous = index
            weight = fractions.Fraction(raw)
            assert weight > 0
            place, constraint, sign = rows[index]
            if place is not None:
                coefficients[place] += weight
                rhs -= weight * problem['initial'][place]
            else:
                weight *= sign
                rhs += weight * (constraint['bound'] - sum(a*m for a,m in zip(constraint['coefficients'], problem['initial'])))
                for i, a in enumerate(constraint['coefficients']): coefficients[i] += weight * a
        assert rhs > 0
        for transition in problem['transitions']:
            delta = sum(coefficients[i]*w for i,w in transition['post']) - sum(coefficients[i]*w for i,w in transition['pre'])
            assert delta <= 0
        return 'python-sparse-farkas'
    if kind == 'projected-closure-v1':
        selected = proof['places']
        assert selected == sorted(set(selected)) and all(type(i) is int and 0 <= i < len(problem['places']) for i in selected)
        ids = {p:i for i,p in enumerate(selected)}
        assert all(a == 0 or i in ids for c in problem['target'] for i,a in enumerate(c['coefficients']))
        transitions, seen = [], set()
        for t in problem['transitions']:
            pre,post = [tuple(sorted((ids[i],w) for i,w in t[k] if i in ids)) for k in ('pre','post')]
            if pre == post or (pre,post) in seen: continue
            seen.add((pre,post)); transitions.append(dict(name=f'p{len(transitions)}',pre=pre,post=post))
        projected = dict(places=[problem['places'][i] for i in selected], initial=[problem['initial'][i] for i in selected], transitions=transitions,
                         target=[dict(c,coefficients=[c['coefficients'][i] for i in selected]) for c in problem['target']])
        verify_threshold_closure(projected, proof['closure'])
        return 'python-projected-closure'
    if kind == 'interval-invariant-v1':
        controls, regions, exclusions = proof['controls'], proof['regions'], proof['exclusions']
        n = len(problem['places'])
        assert controls == sorted(set(controls)) and all(type(i) is int and 0 <= i < n for i in controls)
        assert regions and len(regions) == len(exclusions)
        keys = {}
        def contained(a, b):
            return all(x <= y for x,y in zip(a['lower'],b['lower'])) and all(
                hi is None or (v is not None and v <= hi) for hi,v in zip(a['upper'],b['upper']))
        for region in regions:
            assert len(region['lower']) == len(region['upper']) == n
            assert all(type(lo) is int and 0 <= lo < 2**64 and (hi is None or type(hi) is int and lo <= hi < 2**64)
                       for lo,hi in zip(region['lower'],region['upper']))
            assert all(region['upper'][i] == region['lower'][i] for i in controls)
            key = tuple(region['lower'][i] for i in controls)
            assert key not in keys
            keys[key] = region
        initial = dict(lower=problem['initial'], upper=problem['initial'])
        assert contained(keys[tuple(problem['initial'][i] for i in controls)], initial)
        for region, exclusion in zip(regions, exclusions):
            for t in problem['transitions']:
                if any(region['upper'][i] is not None and region['upper'][i] < w for i,w in t['pre']):
                    continue
                nxt = copy.deepcopy(region)
                for i,w in t['pre']:
                    nxt['lower'][i] = max(nxt['lower'][i],w)-w
                    if nxt['upper'][i] is not None: nxt['upper'][i] -= w
                for i,w in t['post']:
                    nxt['lower'][i] += w
                    if nxt['upper'][i] is not None: nxt['upper'][i] += w
                assert contained(keys[tuple(nxt['lower'][i] for i in controls)], nxt)
            augmented = copy.deepcopy(problem)
            for i,(lo,hi) in enumerate(zip(region['lower'],region['upper'])):
                cs = [0]*n; cs[i] = 1
                augmented['target'].append(dict(coefficients=cs,bound=lo,equality=False))
                if hi is not None:
                    cs = [0]*n; cs[i] = -1
                    augmented['target'].append(dict(coefficients=cs,bound=-hi,equality=False))
            if exclusion['kind'] == 'farkas':
                verify(augmented,dict(verdict='unreachable',certificate=exclusion['certificate']))
            else:
                assert exclusion['kind'] == 'integer-cuts-v1'
                verify_proof(augmented,exclusion)
        return 'python-interval-invariant'
    if kind == 'threshold-closure-v1':
        return verify_threshold_closure(problem, proof)
    if kind == 'integer-cuts-v1':
        originals = original_rows(problem)
        rows = []
        for node in proof['nodes']:
            if node['rule'] == 'original':
                assert 0 <= node['index'] < len(originals)
                a,b = originals[node['index']]
            else:
                assert node['rule'] == 'combine'
                assert 0 <= node['left'] < len(rows) and 0 <= node['right'] < len(rows)
                u,v = int(node['left_weight']),int(node['right_weight'])
                assert u >= 0 and v >= 0
                x,c = rows[node['left']]; y,d = rows[node['right']]
                a,b = [u*i+v*j for i,j in zip(x,y)],u*c+v*d
            g = math.gcd(*a)
            if g: a,b = [x//g for x in a],-((-b)//g)
            rows.append((a,b))
        assert 0 <= proof['contradiction'] < len(rows)
        a,b = rows[proof['contradiction']]
        assert not any(a) and b > 0
        return 'python-integer-cuts'
    augmented = copy.deepcopy(problem)
    if kind == 'marked-traps':
        sets = proof['traps']
    else:
        assert kind == 'empty-siphon'
        sets = [proof['empty_siphon']]
    for places in sets:
        chosen = set(places)
        assert len(chosen) == len(places) and all(0 <= p < len(problem['places']) for p in places)
        if kind == 'marked-traps':
            assert any(problem['initial'][p] for p in chosen)
        else:
            assert all(problem['initial'][p] == 0 for p in chosen)
        for t in problem['transitions']:
            pre = any(p in chosen for p,w in t['pre'])
            post = any(p in chosen for p,w in t['post'])
            assert (not pre or post) if kind == 'marked-traps' else (not post or pre)
        augmented['target'].append(dict(coefficients=[int(p in chosen) for p in range(len(problem['places']))],
            bound=1 if kind == 'marked-traps' else 0,equality=kind == 'empty-siphon'))
    verify(augmented,dict(verdict='unreachable',certificate=proof['certificate']))
    return 'python-'+kind

def verify(problem, answer):
    if answer['verdict'] == 'reachable':
        m = problem['initial'][:]
        for i in answer['trace']:
            assert 0 <= i < len(problem['transitions'])
            t = problem['transitions'][i]
            for p,w in t['pre']: assert m[p] >= w
            for p,w in t['pre']: m[p] -= w
            for p,w in t['post']: m[p] += w
        reported = answer['marking']
        if reported is None and answer.get('proof',{}).get('kind') == 'big-witness':
            reported = list(map(int,answer['proof']['marking']))
        assert m == reported
        for c in problem['target']:
            a = sum(x*y for x,y in zip(c['coefficients'],m))
            assert a == c['bound'] if c['equality'] else a >= c['bound']
        return 'python-witness'
    if answer['verdict'] == 'unreachable' and answer.get('proof'):
        return verify_proof(problem,answer['proof'])
    if answer['verdict'] == 'unreachable' and answer.get('certificate'):
        n = len(problem['transitions'])
        rows = original_rows(problem)
        weights = list(map(fractions.Fraction,answer['certificate']))
        assert len(weights) == len(rows) and all(w >= 0 for w in weights)
        assert all(sum(w*a[t] for w,(a,b) in zip(weights,rows)) == 0 for t in range(n))
        assert sum(w*b for w,(a,b) in zip(weights,rows)) > 0
        return 'python-farkas'
    if answer['verdict'] == 'unreachable' and answer.get('reason') == 'finite reachable state space exhausted':
        initial = tuple(problem['initial'])
        seen = {initial}; pending = collections.deque([initial])
        while pending:
            m = pending.popleft()
            accepted = True
            for c in problem['target']:
                value = sum(x*y for x,y in zip(c['coefficients'],m))
                accepted &= (value == c['bound'] if c['equality'] else value >= c['bound'])
            assert not accepted
            for t in problem['transitions']:
                if any(m[p] < w for p,w in t['pre']): continue
                nxt = list(m)
                for p,w in t['pre']: nxt[p] -= w
                for p,w in t['post']: nxt[p] += w
                nxt = tuple(nxt)
                if nxt not in seen:
                    if len(seen) >= 200_000: return 'none-checker-state-limit'
                    seen.add(nxt); pending.append(nxt)
        return 'python-finite-closure'
    if answer['verdict'] == 'unreachable' and answer.get('method') == 'kosaraju':
        return 'none-decomposition-certificate'
    return 'none'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=3)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--max-states', type=int, default=200000)
    parser.add_argument('--methods', nargs='+', default=['bfs','best-first','state-equation','integer-state-equation','marked-traps','support','klm-schemes','portfolio','smpt'])
    parser.add_argument('--output', default='results/initial')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    queries = sorted((ROOT/'benchmarks/serializability').glob('*/smpt_petri_disjunct_*.net'))
    metadata = dict(platform=platform.platform(), processor=platform.processor(), seconds=args.seconds, repeat=args.repeat, methods=args.methods, max_states=args.max_states,
        rustc=subprocess.check_output(['rustc','--version'],text=True).strip(), z3=subprocess.check_output([str(ROOT/'vendor/venv/bin/z3'),'-version'],text=True).strip(),
        comparison='Sequential backend-only cold process wall time; no frontend or frontend proof validation. Native witness/Farkas verification included internally. SMPT exports proofs.', queries=len(queries), binary_sha256=hashlib.sha256((ROOT/'target/release/vass-reach').read_bytes()).hexdigest(), source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').glob('*.rs'))})
    if 'kreach' in args.methods:
        metadata['kreach_sha256'] = hashlib.sha256((ROOT/'vendor/KReach/bin/kosaraju').read_bytes()).hexdigest()
        metadata['kreach_note'] = 'Unverified external Kosaraju implementation, GHC 9.14.1/SBV 14.5 adaptation; failed direct-encoding smoke tests. Uses single-state pure-VAS encoding; conversion outside timing; Z3 arithmetic; no exported certificate.'
    metadata['load_at_start'] = os.getloadavg()
    metadata['timing_note'] = 'Other user compiler workloads were active during this session; wall timings are exploratory, not isolated-machine measurements.'
    (out/'environment.json').write_text(json.dumps(metadata,indent=2))
    with (out/'runs.jsonl').open('w') as records:
        for net in queries:
            name = net.parent.name+'_'+net.stem.removeprefix('smpt_petri_')
            if args.filter and not re.search(args.filter,name): continue
            xml = net.with_name(net.name.replace('petri','constraints')).with_suffix('.xml')
            digest = hashlib.sha256(net.read_bytes()+xml.read_bytes()).hexdigest()
            for repeat in range(args.repeat):
                # Alternate execution order to reduce systematic order bias.
                methods = args.methods if repeat%2 == 0 else args.methods[::-1]
                for method in methods:
                    prefix = out / f'{name}.{method}.{repeat}'
                    log = prefix.with_suffix(prefix.suffix+'.log')
                    if method == 'kreach':
                        problem_file = out/(name+'.json')
                        if not problem_file.exists():
                            subprocess.run([str(ROOT/'target/release/vass-reach'),'--net',str(net),'--xml',str(xml),'--method','state-equation','--seconds','0.000001','--export-json',str(problem_file)],stdout=subprocess.DEVNULL,check=True)
                        mist_file = out/(name+'.mist')
                        mist_file.write_text(mist(json.loads(problem_file.read_text())))
                        command = [str(ROOT/'vendor/KReach/bin/kosaraju'),'--reach','--quiet',str(mist_file),'+RTS','-N1','-RTS']
                        cwd = ROOT
                    elif method == 'smpt':
                        command = [str(ROOT/'vendor/venv/bin/python'),'-m','smpt','-n',str(net),'--xml',str(xml),'--show-time','--show-model','--debug','--export-proof',str(prefix)+'.proof','--methods','STATE-EQUATION','BMC','--timeout',str(args.seconds)]
                        cwd = ROOT/'vendor/SMPT'
                    else:
                        command = [str(ROOT/'target/release/vass-reach'),'--net',str(net),'--xml',str(xml),'--method',method,'--seconds',str(args.seconds),'--max-states',str(args.max_states),'--export-json',str(out/(name+'.json'))]
                        cwd = ROOT
                    # SMPT finds z3 via PATH, as in the artifact wrapper.
                    os.environ['PATH'] = str(ROOT/'vendor/venv/bin') + os.pathsep + os.environ['PATH']
                    os.environ['KOSARAJU_SOLVER'] = 'z3'
                    wall, code, timeout = run(command,cwd,args.seconds if method == 'kreach' else args.seconds+3,log)
                    record = dict(query=name,method=method,repeat=repeat,sha256=digest,wall_seconds=wall,exit_code=code,outer_timeout=timeout,verdict='unknown')
                    text = log.read_text()
                    if method == 'kreach':
                        if code == 0:
                            if text.strip().splitlines()[-1:] == ['Reachable']: record['verdict'] = 'reachable'
                            elif text.strip().splitlines()[-1:] == ['Unreachable']: record['verdict'] = 'unreachable'
                            else: record['verdict'] = 'error'; record['error'] = 'unrecognized KReach output'
                        elif not timeout: record['verdict'] = 'error'
                        record['independent_check'] = 'none-external-kreach'
                    elif method == 'smpt':
                        match = re.search(r'^FORMULA \S+ (TRUE|FALSE)(?: TIME ([0-9.]+))?',text,re.M)
                        if match:
                            record['verdict'] = 'reachable' if match[1] == 'TRUE' else 'unreachable'
                            if match[2]: record['reported_seconds'] = float(match[2])
                    elif code == 0:
                        try:
                            answer = json.loads(text)
                            record['engine'] = answer['method']
                            record.update({k:v for k,v in answer.items() if k != 'method'})
                            record['independent_check'] = verify(json.loads((out/(name+'.json')).read_text()),answer)
                        except Exception as e:
                            record['verdict'] = 'error'; record['error'] = repr(e)
                    else:
                        if not timeout: record['verdict'] = 'error'
                    # Full witnesses/certificates remain in logs; compact timing table here.
                    for field in ('trace','marking','certificate','proof'): record.pop(field,None)
                    records.write(json.dumps(record)+'\n'); records.flush()
                    print(f"{name:22} {method:15} {record['verdict']:12} {wall:.4f}s",flush=True)
if __name__ == '__main__': main()
