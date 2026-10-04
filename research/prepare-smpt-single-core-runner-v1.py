"""Prepare opt-in SMPT configurations without touching active runners."""
from pathlib import Path
import argparse
import gzip
import hashlib
import io
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'results/runner-threshold-v1'
BENCHMARK = 'scripts/benchmark_smpt_classic.py'
PARENT_BENCHMARK_SHA256 = '3824a92df5868ccf990a1475f3e1edb3125d7ccb32f1df842a33fc8c0b85698c'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected unique source fragment: {old!r}')
    return text.replace(old, new)


def extend(text):
    text = replace_once(text, '\n\ndef execute(', '''

SMPT_SINGLE_CORE_MODES = {
    'smpt-compact-portable': ['WALK', 'STATE-EQUATION', 'BMC', 'K-INDUCTION', 'SMT'],
    'smpt-pdr-reach-portable': ['PDR-REACH', 'SMT'],
    'smpt-pdr-saturated-portable': ['PDR-REACH-SATURATED', 'SMT'],
    'smpt-mcc-portable': SMPT_MODES['smpt-full'],
}
SMPT_MODES.update(SMPT_SINGLE_CORE_MODES)


def smpt_scheduling(method):
    return dict(requested_methods=SMPT_MODES[method], effective_workers=None,
                requested_methods_control_workers=method != 'smpt-mcc-portable',
                scheduling_policy=('official-mcc' if method == 'smpt-mcc-portable'
                                   else 'requested-method-portfolio'),
                effective_workers_note=('Official MCC chooses workers; --methods satisfies the required CLI group and is ignored for scheduling.'
                                        if method == 'smpt-mcc-portable' else
                                        'Chosen dynamically by SMPT; requested methods are not worker counts or execution order.'))


def execute(''')
    text = replace_once(text,
        "    command = [str(args.smpt_python), '-m', 'smpt',",
        "    method_options = ['--methods', *SMPT_MODES[method]]\n"
        "    if method == 'smpt-mcc-portable':\n"
        "        method_options.append('--mcc')\n"
        "    command = [str(args.smpt_python), '-m', 'smpt',")
    text = replace_once(text,
        "               '--methods', *SMPT_MODES[method], '--timeout', str(math.ceil(args.seconds)),",
        "               *method_options, '--timeout', str(math.ceil(args.seconds)),")
    text = replace_once(text,
        "    if args.auto_reduce or method.startswith('smpt-full'):",
        "    if args.auto_reduce or method.startswith('smpt-full') or method in SMPT_SINGLE_CORE_MODES:")
    text = replace_once(text,
        "    contents = log.read_text()\n    capability_failures",
        "    if method in SMPT_SINGLE_CORE_MODES:\n"
        "        expired = expired or wall > args.seconds\n"
        "    contents = log.read_text()\n    capability_failures")
    text = replace_once(text,
        "    if expired and getattr(args, 'linux_cpus', None):",
        "    if expired and (getattr(args, 'linux_cpus', None) or method in SMPT_SINGLE_CORE_MODES):")
    text = replace_once(text,
        "                outer_timeout=expired, enabled_methods=SMPT_MODES[method],",
        "                outer_timeout=expired,\n"
        "                **(smpt_scheduling(method) if method in SMPT_SINGLE_CORE_MODES\n"
        "                   else dict(enabled_methods=SMPT_MODES[method])),")
    text = replace_once(text,
        "                formula_output=next((line for line in contents.splitlines() if line.startswith('FORMULA ')), None),",
        "                formula_output=next((line for line in contents.splitlines()\n"
        "                                     if line.startswith('FORMULA ' + query['property_id'] + ' '\n"
        "                                                        if method in SMPT_SINGLE_CORE_MODES else 'FORMULA ')), None),")
    text = replace_once(text,
        "    if any(m.startswith('smpt-full') for m in args.methods):",
        "    if any(m.startswith('smpt-full') or m in SMPT_SINGLE_CORE_MODES for m in args.methods):")
    text = replace_once(text,
        "                    row['execution_attempted'] = query['status'] == 'imported'",
        "                    if method in SMPT_SINGLE_CORE_MODES:\n"
        "                        row.update(smpt_scheduling(method))\n"
        "                    row['execution_attempted'] = query['status'] == 'imported'")
    text = replace_once(text,
        "    environment['input_preflight'] = dict(mode='streaming-deduplicated-sha256',",
        "    if any(m in SMPT_SINGLE_CORE_MODES for m in args.methods):\n"
        "        environment['smpt_scheduling'] = {m: smpt_scheduling(m)\n"
        "                                          for m in args.methods if m in SMPT_MODES}\n"
        "        environment['smpt_auto_reduce_by_method'] = {\n"
        "            m: args.auto_reduce or m.startswith('smpt-full') or m in SMPT_SINGLE_CORE_MODES\n"
        "            for m in args.methods if m in SMPT_MODES}\n"
        "        environment['smpt'] = ('Selected source directory. Requested methods are not effective workers. '\n"
        "            'Official --mcc selects its own preliminary and subsequent portfolios. '\n"
        "            'All added portable configurations require automatic reduction and resource tracking. '\n"
        "            'Internal timeout ceil(seconds); outer allowance seconds plus configured grace '\n"
        "            '(default zero on Linux, one second elsewhere). Added configurations reject '\n"
        "            'expired or over-budget answers. External proofs are not independently checked. '\n"
        "            'See linux_cpus, perf and per-row resources for enforcement.')\n"
        "    environment['input_preflight'] = dict(mode='streaming-deduplicated-sha256',")
    return text


def prepare(out):
    parents = json.loads((PARENT / 'files-sha256.json').read_text())
    if len(parents) != 24 or parents[BENCHMARK] != PARENT_BENCHMARK_SHA256:
        raise ValueError('Unexpected parent runner manifest')
    payload = {}
    for name, expected in parents.items():
        data = (PARENT / 'source' / name).read_bytes()
        if sha(data) != expected:
            raise ValueError(f'Parent hash mismatch: {name}')
        payload[name] = data
    payload[BENCHMARK] = extend(payload[BENCHMARK].decode()).encode()
    compile(payload[BENCHMARK], BENCHMARK, 'exec')
    files = {name: sha(data) for name, data in sorted(payload.items())}
    changes = [name for name in parents if parents[name] != files[name]]
    if changes != [BENCHMARK]:
        raise ValueError(f'Unexpected changes: {changes}')
    out.mkdir()
    for name, data in payload.items():
        target = out / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (out / 'files-sha256.json').write_text(json.dumps(files, indent=2) + '\n')
    with (out / 'runner.tar.gz').open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for name, data in sorted(payload.items()):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(data), 0o644, 0
                    archive.addfile(info, io.BytesIO(data))
    provenance = dict(parent=str(PARENT.relative_to(ROOT)), parent_files=parents,
        files=files, changes=changes, additions=[],
        archive_sha256=sha((out / 'runner.tar.gz').read_bytes()),
        preparer_sha256=sha(Path(__file__).read_bytes()),
        scope='Opt-in portable SMPT configuration screen; no experiment frozen or executed. Existing configurations retain their commands and behavior.')
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/runner-smpt-single-core-v1')
    args = parser.parse_args()
    result = prepare(args.output)
    print(json.dumps(dict(files=len(result['files']), changes=result['changes'],
                          archive_sha256=result['archive_sha256'])))
