#!/usr/bin/env python3
"""Acquire only pinned, unpruned repository benchmark pairs; never run upstream code."""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request

COMMIT = 'bf6bb6fefd03c640af25b2f5ea0a0dc053d47736'
REPOSITORY = 'https://github.com/p-offtermatt/FastForward'
SUITES = ('coverability', 'random_walk', 'sypet')
PREFIX = 'artifact/benchmark/nets/'
METADATA = {'LICENSE.txt', 'README.md', 'artifact/benchmark/run_all_on_all.sh',
            'artifact/benchmark/run_all_fastforward.sh', 'artifact/benchmark/benchmark.py',
            'artifact/benchmark/benchmark_utils.py',
            'artifact/benchmark/generate_random_walk_benchmarks.py',
            'artifact/benchmark/nets/coverability/convert.py'}

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'pvass-benchmark-acquisition'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path, default=pathlib.Path('benchmarks/fastforward-repository-v1'))
    parser.add_argument('--tree', type=pathlib.Path)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 8:
        parser.error('--jobs must be 1..8')
    tree_url = f'https://api.github.com/repos/p-offtermatt/FastForward/git/trees/{COMMIT}?recursive=1'
    tree_bytes = args.tree.read_bytes() if args.tree else fetch(tree_url)
    tree = json.loads(tree_bytes)
    if tree.get('truncated') or tree.get('sha') != COMMIT:
        raise ValueError('wrong or incomplete pinned repository tree')
    args.output.mkdir(parents=True, exist_ok=True)
    tree_file = args.output / 'repository-tree.json'
    if tree_file.exists() and tree_file.read_bytes() != tree_bytes:
        raise ValueError('refusing to replace differing repository tree')
    tree_file.write_bytes(tree_bytes)
    entries = []
    for item in tree['tree']:
        path = item['path']
        selected = any(path.startswith(PREFIX + suite + '/') for suite in SUITES) and path.endswith(('.lola', '.formula'))
        if item['type'] == 'blob' and (selected or path in METADATA):
            if item['mode'] not in ('100644', '100755') or '..' in pathlib.PurePosixPath(path).parts:
                raise ValueError(f'unsupported source path or mode: {path}')
            entries.append(item)
    def acquire(item):
        path = item['path']
        destination = args.output / 'upstream' / path
        url = f'https://raw.githubusercontent.com/p-offtermatt/FastForward/{COMMIT}/' + urllib.parse.quote(path, safe='/')
        data = destination.read_bytes() if destination.exists() else fetch(url)
        git_sha = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        if len(data) != item['size'] or git_sha != item['sha']:
            raise ValueError(f'upstream blob mismatch: {path}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + '.part')
            temporary.write_bytes(data)
            temporary.replace(destination)
        return {'path': path, 'bytes': len(data), 'git_blob_sha1': git_sha,
                'sha256': hashlib.sha256(data).hexdigest(), 'url': url}
    completed = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i, result in enumerate(pool.map(acquire, entries), 1):
            completed.append(result)
            if i % 50 == 0:
                print(f'verified {i}/{len(entries)} files', flush=True)
    suites = {}
    for suite in SUITES:
        files = [e for e in completed if e['path'].startswith(PREFIX + suite + '/')]
        nets = {e['path'][:-5] for e in files if e['path'].endswith('.lola')}
        formulas = {e['path'][:-8] for e in files if e['path'].endswith('.formula')}
        if nets != formulas:
            raise ValueError(f'unpaired files in {suite}')
        suites[suite] = {'queries': len(nets), 'files': len(files), 'bytes': sum(e['bytes'] for e in files)}
    manifest = {'format': 'fastforward-source-acquisition-v1', 'repository': REPOSITORY,
                'commit': COMMIT, 'repository_tree_url': tree_url,
                'repository_tree_sha256': hashlib.sha256(tree_bytes).hexdigest(),
                'scope': 'Unpruned repository .lola/.formula pairs only. Not the archived paper artifact. Source acquisition does not establish solver-ready conversion or verified verdicts.',
                'excluded': ['prepruned suites', 'workflow datasets', 'alternative .tts/.spec/.prop encodings', 'archived figshare artifact'],
                'license_path': 'upstream/LICENSE.txt', 'suites': suites, 'files': completed}
    output = args.output / 'acquisition.json'
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    if output.exists() and output.read_text() != encoded:
        raise ValueError('refusing to replace differing acquisition manifest')
    output.write_text(encoded)
    print(json.dumps(suites, indent=2), flush=True)

if __name__ == '__main__':
    main()
