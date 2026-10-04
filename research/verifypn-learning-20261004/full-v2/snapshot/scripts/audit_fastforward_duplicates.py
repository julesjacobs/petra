#!/usr/bin/env python3
"""Compare exact indexed net/target semantics; not a graph-isomorphism check."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def key(problem):
    constraints = []
    for constraint in problem['target']:
        terms = [(i, a) for i, a in enumerate(constraint['coefficients']) if a]
        # Only an obvious nonnegative singleton lower bound is tautological.
        if not constraint['equality'] and len(terms) == 1 and terms[0][1] == 1 and constraint['bound'] == 0:
            continue
        constraints.append({'terms': terms, 'bound': constraint['bound'], 'equality': constraint['equality']})
    semantic = {'initial': problem['initial'],
                'transitions': [{'pre': t['pre'], 'post': t['post']} for t in problem['transitions']],
                'target': constraints}
    return hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--new', type=Path, default=Path('benchmarks/fastforward-import-v2/manifest.json'))
    parser.add_argument('--existing', type=Path, default=Path('benchmarks/smpt-classic/manifest.json'))
    parser.add_argument('--output', type=Path, default=Path('research/fastforward-indexed-duplicate-audit.json'))
    args = parser.parse_args()
    index = defaultdict(list)
    counts = {}
    for kind, path in [('existing', args.existing), ('fastforward', args.new)]:
        manifest = json.loads(path.read_text())
        counts[kind] = {'queries': len(manifest['queries']), 'compared_branches': 0, 'excluded_queries': 0}
        for row in manifest['queries']:
            if row['status'] != 'imported':
                counts[kind]['excluded_queries'] += 1
                continue
            for branch in row['branches']:
                data = (path.parent / branch['path']).read_bytes()
                if hashlib.sha256(data).hexdigest() != branch['sha256']:
                    raise ValueError('canonical branch SHA256 mismatch')
                index[key(json.loads(data))].append({'corpus': kind, 'query': row['name'], 'branch': branch['path']})
                counts[kind]['compared_branches'] += 1
    groups = [rows for rows in index.values() if len(rows) > 1]
    cross = [rows for rows in groups if len({r['corpus'] for r in rows}) > 1]
    report = {'scope': 'Exact indexed semantics after removing labels and nonnegative singleton >=0 tautologies. Place, transition and constraint order retained. No arbitrary-renaming/isomorphism or full logical-equivalence check; no duplicate finding does not establish suite disjointness.',
              'manifests': [str(args.new), str(args.existing)], 'counts': counts,
              'groups': groups, 'cross_corpus_groups': cross}
    if args.output.exists():
        raise ValueError('refusing to overwrite duplicate audit')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'counts': counts, 'duplicate_groups': len(groups), 'cross_corpus_groups': len(cross)}))

if __name__ == '__main__':
    main()
