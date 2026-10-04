#!/usr/bin/env python3
"""Reduce conjunctions of signed linear targets to exact Petri-net reachability."""
import json
import pathlib
import sys

def reduce_problem(problem):
    n = len(problem['places']); rows = problem['target']
    run, check = n, n+1
    places = [f'p{i}' for i in range(n+2+2*len(rows))]
    initial = problem['initial'][:] + [1,0] + [0]*(2*len(rows))
    goal = [0]*len(places); goal[check] = 1
    transitions = []
    def add(pre,post):
        transitions.append(dict(name=f't{len(transitions)}',pre=pre,post=post))
    for t in problem['transitions']:
        add(t['pre']+[(run,1)],t['post']+[(run,1)])
    constants = [(check,1)]
    for i,c in enumerate(rows):
        left,right = n+2+2*i,n+3+2*i
        if c['bound'] < 0: constants.append((left,-c['bound']))
        if c['bound'] > 0: constants.append((right,c['bound']))
    add([(run,1)],constants)
    for p in range(n):
        post = [(check,1)]
        for i,c in enumerate(rows):
            a = c['coefficients'][p]
            if a: post.append((n+2+2*i+int(a<0),abs(a)))
        add([(check,1),(p,1)],post)
    for i,c in enumerate(rows):
        left,right = n+2+2*i,n+3+2*i
        add([(check,1),(left,1),(right,1)],[(check,1)])
        if not c['equality']:
            add([(check,1),(left,1)],[(check,1)])
    return dict(places=places,initial=initial,transitions=transitions,
        target=[dict(coefficients=[int(i==j) for i in range(len(places))],bound=x,equality=True) for j,x in enumerate(goal)])

def split_transitions(problem):
    n = len(problem['places'])
    idle = n
    total = n+1+len(problem['transitions'])
    transitions = []
    for i,t in enumerate(problem['transitions']):
        intermediate = n+1+i
        transitions.append(dict(name=f'consume{i}',pre=t['pre']+[(idle,1)],post=[(intermediate,1)]))
        transitions.append(dict(name=f'produce{i}',pre=[(intermediate,1)],post=t['post']+[(idle,1)]))
    target = [dict(coefficients=c['coefficients']+[0]*(total-n),bound=c['bound'],equality=c['equality']) for c in problem['target']]
    for j in range(n,total):
        target.append(dict(coefficients=[int(i==j) for i in range(total)],bound=int(j==idle),equality=True))
    return dict(places=[f'p{i}' for i in range(total)],initial=problem['initial']+[1]+[0]*len(problem['transitions']),transitions=transitions,target=target)

def mist(problem):
    reduced = split_transitions(reduce_problem(problem))
    lines = ['vars',' '.join(reduced['places']),'rules']
    for t in reduced['transitions']:
        entries = [f"p{p}' = p{p} -{w}" for p,w in t['pre']]
        entries += [f"p{p}' = p{p} +{w}" for p,w in t['post']]
        lines.append(' -> '+', '.join(entries)+';')
    lines += ['init',', '.join(f'p{i} = {x}' for i,x in enumerate(reduced['initial'])),
        'target',', '.join(f'p{i} = {c["bound"]}' for i,c in enumerate(reduced['target']))]
    return '\n'.join(lines)+'\n'

def kvass(problem):
    n = len(problem['places']); rows = problem['target']
    dimension = n+2*len(rows)
    edges = []
    private = 2
    def add(source, destination, pre, post):
        nonlocal private
        consume = [0]*dimension; produce = [0]*dimension
        for p,w in pre: consume[p] -= w
        for p,w in post: produce[p] += w
        edges.append((source,private,consume))
        edges.append((private,destination,produce))
        private += 1
    for t in problem['transitions']:
        add(0,0,t['pre'],t['post'])
    constants = []
    for i,c in enumerate(rows):
        if c['bound'] < 0: constants.append((n+2*i,-c['bound']))
        if c['bound'] > 0: constants.append((n+2*i+1,c['bound']))
    add(0,1,[],constants)
    for p in range(n):
        post = []
        for i,c in enumerate(rows):
            a = c['coefficients'][p]
            if a: post.append((n+2*i+int(a<0),abs(a)))
        add(1,1,[(p,1)],post)
    for i,c in enumerate(rows):
        add(1,1,[(n+2*i,1),(n+2*i+1,1)],[])
        if not c['equality']: add(1,1,[(n+2*i,1)],[])
    return repr((0,problem['initial']+[0]*(2*len(rows)),1,[0]*dimension,edges))+'\n'

if __name__ == '__main__':
    pathlib.Path(sys.argv[2]).write_text(mist(json.loads(pathlib.Path(sys.argv[1]).read_text())))
