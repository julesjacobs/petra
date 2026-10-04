#!/usr/bin/env python3
"""Check the manually supplied control-dependent invariant with exact integers."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = json.loads((ROOT / 'results/portfolio-larger-budget/g2_disjunct_1.json').read_text())
# These indices name the exact artifact instance; this is a proof checker,
# not a heuristic that purports to discover the partition.
pre = {0, 31, 26}
low = {32, 33, 34, 35, 36}
high = {27, 28, 29, 30}
control = pre | low | high
c300 = {18, 19}  # pending and delivered transfer responses
c350 = {22, 23}
assert {i for i,n in enumerate(p['places']) if n.startswith('G_')} == control
assert sum(p['initial'][i] for i in control) == 1
assert p['initial'][0] == 1
assert all(p['initial'][i] == 0 for i in c300 | c350)

checks = 0
for t in p['transitions']:
    before, after = dict(t['pre']), dict(t['post'])
    ins = [(i,w) for i,w in t['pre'] if i in control]
    outs = [(i,w) for i,w in t['post'] if i in control]
    assert sum(w for _,w in ins) == sum(w for _,w in outs)
    # Each event either preserves the control token or moves exactly one.
    assert len(ins) <= 1 and len(outs) <= 1
    assert all(w == 1 for _,w in ins + outs)
    d300 = sum(after.get(i,0)-before.get(i,0) for i in c300)
    d350 = sum(after.get(i,0)-before.get(i,0) for i in c350)
    for q in control:
        if ins and ins[0][0] != q:
            continue
        r = outs[0][0] if outs else q
        if q in pre:
            # In pre: C300=C350=0.
            if r in pre:
                assert d300 == d350 == 0
            elif r in low:
                assert d350 == 0
            else:
                assert d300-d350+int(r==30) <= 0
        elif q in low:
            # In low: C350=0; the region is closed.
            assert r in low and d350 == 0
        else:
            # In high: C300-C350+[q=30] <= 0.
            assert r in high
            assert d300-d350+int(r==30)-int(q==30) <= 0
        checks += 1

zero = set()
for c in p['target']:
    nonzero = [(i,a) for i,a in enumerate(c['coefficients']) if a]
    if c['equality'] and c['bound'] == 0 and len(nonzero)==1:
        zero.add(nonzero[0][0])
assert {18,22} <= zero
assert any(not c['equality'] and c['bound']==1 and
           c['coefficients']==[int(i==23) for i in range(len(p['places']))]
           for c in p['target'])
assert any(not c['equality'] and c['bound']==1 and
           c['coefficients']==[int(i==19)-int(i==23) for i in range(len(p['places']))]
           for c in p['target'])
# Target C350>=1 excludes pre/low. In high, with pending counters zero,
# R300-R350 <= -[q=30] <= 0 contradicts target R300-R350>=1.
print(f'UNREACHABLE: checked control invariant, {checks} transition/control cases, and target contradiction.')
