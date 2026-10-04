#!/usr/bin/env python3
"""Collect immutable stress selection with one bounded worker per model.

No solver is run. Every planned property slot survives download/import failure.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import signal
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.part')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


class ArtifactLimit(RuntimeError):
    pass


class ArtifactBudget:
    def __init__(self, limit):
        self.limit = limit
        self.used = 0
        self.categories = {}

    def write(self, stream, data, category):
        if self.used + len(data) > self.limit:
            raise ArtifactLimit(f'Artifact byte limit {self.limit} exceeded at {self.used} bytes')
        written = stream.write(data)
        if written != len(data):
            raise OSError('Incomplete artifact write')
        self.used += written
        self.categories[category] = self.categories.get(category, 0) + written
        return written

    def stats(self):
        return dict(limit_bytes=self.limit, used_bytes=self.used, categories=self.categories.copy())


def write_text_chunks(path, chunks, budget, category='canonical'):
    with path.open('xb') as stream:
        for chunk in chunks:
            for offset in range(0, len(chunk), 16384):
                budget.write(stream, chunk[offset:offset+16384].encode(), category)


def write_canonical_json(path, value, budget):
    encoder = json.JSONEncoder(separators=(',', ':'))
    def chunks():
        yield from encoder.iterencode(value)
        yield '\n'
    write_text_chunks(path, chunks(), budget)


def tina_chunks(problem):
    def arcs(values):
        return ' '.join(f'p{i}*{w}' for i, w in values)
    yield 'net imported\n'
    for i, marking in enumerate(problem['initial']):
        yield f'pl p{i} ({marking})\n'
    for i, transition in enumerate(problem['transitions']):
        yield f'tr t{i} {arcs(transition["pre"])} -> {arcs(transition["post"])}\n'


def workload_preflight():
    import psutil
    from process_runner import workspace_workloads
    conflicts = workspace_workloads(ROOT)
    drivers = {'benchmark.py', 'benchmark_smpt_classic.py', 'linux_benchmark_segments.py',
               'collect_stress_mcc.py'}
    for process in psutil.process_iter():
        try:
            if process.pid == os.getpid():
                continue
            name, command = process.name() or '', process.cmdline() or []
            if 'python' not in name.lower() or not any(Path(arg).name in drivers for arg in command):
                continue
            if process.status() != psutil.STATUS_ZOMBIE and Path(process.cwd()).is_relative_to(ROOT):
                conflicts.append(dict(pid=process.pid, name=name, command=command))
        except (psutil.Error, OSError, SystemError):
            pass
    if conflicts:
        raise RuntimeError(f'Active workspace workloads prohibit collection: {conflicts}')


def artifact_usage(output, row, limit):
    categories = {'archive': 0, 'extracted': 0, 'canonical': 0}
    for suffix in ('.tgz', '.part'):
        path = output/'archives'/f'{row["name"]}{suffix}'
        if path.exists():
            categories['archive'] += path.stat().st_size
    for category, directories in [('extracted', [output/'inputs'/row['name']]),
                                  ('canonical', [output/f'{row["name"]}__RC{i:02}'
                                                 for i in range(row['expected_properties'])])]:
        for directory in directories:
            if directory.exists():
                for path in directory.rglob('*'):
                    if path.is_file():
                        categories[category] += path.stat().st_size
    return dict(limit_bytes=limit, used_bytes=sum(categories.values()), categories=categories)


def snapshot_provenance(output):
    import psutil
    snapshot = output/'collector-source'
    snapshot.mkdir()
    sources = {}
    for name in ('collect_stress_mcc.py', 'smpt_import.py', 'process_runner.py'):
        source = ROOT/'scripts'/name
        shutil.copyfile(source, snapshot/name)
        sources[name] = file_sha256(snapshot/name)
    executable = Path(sys.executable)
    runtime = dict(python_executable=str(executable), python_executable_resolved=str(executable.resolve()),
                   python_sha256=file_sha256(executable), version=sys.version,
                   implementation=platform.python_implementation(), prefix=sys.prefix,
                   base_prefix=sys.base_prefix, platform=platform.platform(),
                   psutil_version=psutil.__version__, invocation=sys.argv)
    write_json(output/'collector-provenance.json', dict(sources=sources, runtime=runtime))
    return sources


def safe_extract(archive, destination, model_name, max_bytes, budget=None):
    """Validate every member; extract only the two required regular files."""
    wanted = {f'{model_name}/model.pnml', f'{model_name}/ReachabilityCardinality.xml'}
    observed, total = set(), 0
    with tarfile.open(archive, mode='r|gz') as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '\\' in member.name:
                raise ValueError(f'Unsafe archive path: {member.name!r}')
            if not (member.isfile() or member.isdir()) or member.issparse():
                raise ValueError(f'Unsafe archive member type: {member.name!r}')
            if member.size < 0:
                raise ValueError('Negative archive member size')
            total += member.size
            if total > max_bytes:
                raise ValueError('Archive expanded-size limit exceeded')
            normalized = str(path)
            if normalized not in wanted:
                continue
            if not member.isfile() or normalized in observed:
                raise ValueError(f'Invalid or duplicate required member: {member.name!r}')
            observed.add(normalized)
            target = destination/path
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open('xb') as output:
                while block := source.read(1024*1024):
                    if budget is None:
                        output.write(block)
                    else:
                        budget.write(output, block, 'extracted')
    if observed != wanted:
        raise ValueError(f'Missing required members: {sorted(wanted-observed)}')
    return total


def download(url, target, max_bytes, budget):
    digest, total = hashlib.sha256(), 0
    temporary = target.with_suffix('.part')
    with urllib.request.urlopen(url, timeout=30) as source, temporary.open('xb') as output:
        while block := source.read(1024*1024):
            total += len(block)
            if total > max_bytes:
                raise ValueError('Archive compressed-size limit exceeded')
            digest.update(block)
            budget.write(output, block, 'archive')
    temporary.replace(target)
    return dict(sha256=digest.hexdigest(), bytes=total)


def planned_slots(row, failure, observed=()):
    records = []
    for index in range(row['expected_properties']):
        item = dict(name=f'{row["name"]}__RC{index:02}', suite='stress-development',
                    family=row['family'], family_group=row.get('family_group', row['family']),
                    instance=row['name'], property_slot=index, planned=True,
                    observed=index < len(observed), status='unsupported', error=failure)
        if index < len(observed):
            item.update(observed[index])
        records.append(item)
    return records


def worker(request_path):
    request = json.loads(request_path.read_text())
    row, output = request['model'], Path(request['output'])
    job = Path(request['job'])
    if sys.platform == 'linux':
        import resource
        limit = request['memory_bytes']
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    budget = ArtifactBudget(request['artifact_bytes'])
    progress = dict(stage='download', observed_properties=[], archive=None)
    def checkpoint():
        progress['artifacts'] = budget.stats()
        write_json(job/'progress.json', progress)
    checkpoint()
    try:
        archive = output/'archives'/f'{row["name"]}.tgz'
        progress['archive'] = download(row['url'], archive, request['archive_bytes'], budget)
        progress['stage'] = 'extract'
        checkpoint()
        expanded = safe_extract(archive, output/'inputs', row['name'], request['expanded_bytes'], budget)
        progress.update(stage='parse-properties', archive_expanded_bytes=expanded)
        checkpoint()
        from smpt_import import pnml, properties, translated_xml, xml_tree
        source = output/'inputs'/row['name']
        original_xml = source/'ReachabilityCardinality.xml'
        tree = xml_tree(original_xml)
        if tree.tag != 'property-set' or any(node.tag != 'property' for node in tree):
            raise ValueError('Unexpected property document structure')
        observed = []
        for node in tree:
            metadata = {}
            identifier = node.findtext('id')
            if identifier is not None:
                metadata['property_id'] = identifier
            observed.append(metadata)
        progress.update(stage='parse-net', observed_properties=observed,
                        actual_property_count=len(observed),
                        original_xml_sha256=file_sha256(original_xml),
                        pnml_sha256=file_sha256(source/'model.pnml'))
        checkpoint()
        if len(observed) != row['expected_properties']:
            raise ValueError(f'Expected {row["expected_properties"]} properties, observed {len(observed)}')
        model = pnml(source/'model.pnml')
        progress['stage'] = 'import-properties'
        checkpoint()
        records = planned_slots(row, 'not imported', observed)
        for index, node in enumerate(tree):
            record = records[index]
            directory = output/record['name']
            directory.mkdir()
            single = ET.Element('property-set')
            single.append(node)
            single_path = directory/'original-property.xml'
            write_text_chunks(single_path, (ET.tostring(single, encoding='unicode'), '\n'), budget)
            record.update(pnml=str((source/'model.pnml').relative_to(output)),
                          xml=str(single_path.relative_to(output)),
                          pnml_sha256=progress['pnml_sha256'], xml_sha256=file_sha256(single_path))
            try:
                imported = properties(single_path, model)
                if len(imported) != 1:
                    raise ValueError('Single-property translation changed property count')
                prop = imported[0]
                branches = []
                for j, target in enumerate(prop.pop('targets')):
                    path = directory/f'branch-{j}.json'
                    write_canonical_json(path, dict(model, target=target), budget)
                    branches.append(dict(path=str(path.relative_to(output)), sha256=file_sha256(path)))
                net_path, property_path = directory/'model.net', directory/'property.xml'
                write_text_chunks(net_path, tina_chunks(model), budget)
                write_text_chunks(property_path, (translated_xml(single_path, model['places']),), budget)
                record.update(prop, status='imported', branches=branches, places=len(model['places']),
                              transitions=len(model['transitions']), net=str(net_path.relative_to(output)),
                              property=str(property_path.relative_to(output)),
                              net_sha256=file_sha256(net_path), property_sha256=file_sha256(property_path))
                record.pop('error', None)
            except (ValueError, KeyError, OverflowError) as error:
                record.update(status='unsupported', error=f'{type(error).__name__}: {error}')
        write_json(job/'records.json', records)
        progress['stage'] = 'complete'
        checkpoint()
    except Exception as error:
        progress.update(stage_failed=progress['stage'], stage='failed', error=f'{type(error).__name__}: {error}',
                        failure_reason='artifact-limit' if isinstance(error, ArtifactLimit) else 'import-failure')
        checkpoint()
        return 1
    return 0


def bounded_worker(command, cwd, seconds, memory_bytes, log):
    import psutil
    start = time.monotonic()
    peak, reason = 0, None
    with log.open('w') as stream:
        process = subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        monitored = psutil.Process(process.pid)
        try:
            while process.poll() is None:
                try:
                    peak = max(peak, monitored.memory_info().rss)
                except psutil.NoSuchProcess:
                    pass
                if peak > memory_bytes:
                    reason = 'memory-limit'
                    break
                if time.monotonic()-start >= seconds:
                    reason = 'timeout'
                    break
                time.sleep(0.02)
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait()
    return dict(exit_code=process.returncode, wall_seconds=time.monotonic()-start,
                sampled_peak_rss_bytes=peak, termination_reason=reason,
                memory_limit_bytes=memory_bytes, seconds_limit=seconds,
                sampling_interval_seconds=0.02,
                address_space_limit_bytes=memory_bytes if sys.platform == 'linux' else None)


def collect(selection_path, output, seconds, memory_mib, archive_mib, expanded_mib, artifact_mib=3072):
    if not math.isfinite(seconds) or min(seconds, memory_mib, archive_mib, expanded_mib, artifact_mib) <= 0:
        raise ValueError('Resource limits must be positive')
    selection_bytes = selection_path.read_bytes()
    selection = json.loads(selection_bytes)
    if selection['format'] != 'mcc-stress-selection-v1':
        raise ValueError('Wrong selection format')
    if any(row['expected_properties'] != 16 or row['split'] != 'stress-development' for row in selection['models']):
        raise ValueError('Expected sixteen stress-development property slots per model')
    if selection['expected_properties'] != 16*len(selection['models']):
        raise ValueError('Selection property total disagrees with model slots')
    names = [row['name'] for row in selection['models']]
    if len(set(names)) != len(names) or any('/' in name or '\\' in name or name in ('.', '..') for name in names):
        raise ValueError('Unsafe or duplicate model names')
    if output.exists():
        raise ValueError('Refusing to overwrite corpus')
    workload_preflight()
    output.mkdir(parents=True)
    source_hashes = snapshot_provenance(output)
    for folder in ('archives', 'inputs', 'collection'):
        (output/folder).mkdir()
    (output/'selection.json').write_bytes(selection_bytes)
    records, outcomes, archives = [], [], []
    manifest = dict(format='smpt-classic-v1', source=selection['source'],
                    selection_sha256=hashlib.sha256(selection_bytes).hexdigest(),
                    suite='stress-development', expected_properties=selection['expected_properties'],
                    collection_complete=False,
                    per_model_limits=dict(seconds=seconds, memory_bytes=memory_mib*1024**2,
                                          archive_bytes=archive_mib*1024**2, expanded_bytes=expanded_mib*1024**2,
                                          artifact_bytes=artifact_mib*1024**2),
                    importer_sha256=file_sha256(ROOT/'scripts/smpt_import.py'),
                    collector_sha256=file_sha256(__file__),
                    queries=[slot for row in selection['models']
                             for slot in planned_slots(row, 'collection not attempted')])
    write_json(output/'manifest.json', manifest)
    for row in selection['models']:
        workload_preflight()
        if any(file_sha256(ROOT/'scripts'/name) != expected for name, expected in source_hashes.items()):
            raise RuntimeError('Collector source changed after snapshot')
        job = output/'collection'/row['name']
        job.mkdir()
        request = dict(model=row, output=str(output), job=str(job), memory_bytes=memory_mib*1024**2,
                       archive_bytes=archive_mib*1024**2, expanded_bytes=expanded_mib*1024**2,
                       artifact_bytes=artifact_mib*1024**2)
        write_json(job/'request.json', request)
        usage = bounded_worker([sys.executable, str(Path(__file__).resolve()), '--worker', str(job/'request.json')],
                               ROOT, seconds, memory_mib*1024**2, job/'worker.log')
        progress = json.loads((job/'progress.json').read_text()) if (job/'progress.json').exists() else {}
        usage['artifacts'] = artifact_usage(output, row, artifact_mib*1024**2)
        if progress.get('failure_reason') == 'artifact-limit':
            usage['termination_reason'] = 'artifact-limit'
        success = usage['exit_code'] == 0 and progress.get('stage') == 'complete' and (job/'records.json').exists()
        if success:
            model_records = json.loads((job/'records.json').read_text())
            if len(model_records) != row['expected_properties']:
                raise ValueError('Worker changed planned property count')
        else:
            failure = usage['termination_reason'] or progress.get('error') or f'Worker exit {usage["exit_code"]}'
            model_records = planned_slots(row, failure, progress.get('observed_properties', []))
        records.extend(model_records)
        outcome = dict(model=row['name'], success=success, resources=usage, progress=progress,
                       imported_properties=sum(r['status'] == 'imported' for r in model_records),
                       planned_properties=row['expected_properties'])
        outcomes.append(outcome)
        if progress.get('archive'):
            archives.append(dict(model=row['name'], url=row['url'], **progress['archive']))
        write_json(output/'archive-checksums.json', dict(selection_sha256=manifest['selection_sha256'], archives=archives))
        write_json(output/'collection-outcomes.json', outcomes)
        manifest['queries'] = records + [slot for remaining in selection['models'][len(outcomes):]
                                        for slot in planned_slots(remaining, 'collection not attempted')]
        write_json(output/'manifest.json', manifest)
        print(row['name'], outcome['imported_properties'], '/', row['expected_properties'], usage, flush=True)
    manifest['collection_complete'] = True
    write_json(output/'manifest.json', manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--selection', type=Path, default=ROOT/'benchmarks/stress-selection.json')
    parser.add_argument('--output', type=Path, default=ROOT/'benchmarks/mcc-stress-development')
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--memory-mib', type=int, default=2048)
    parser.add_argument('--archive-mib', type=int, default=512)
    parser.add_argument('--expanded-mib', type=int, default=2048)
    parser.add_argument('--artifact-mib', type=int, default=3072)
    args = parser.parse_args()
    if args.worker:
        raise SystemExit(worker(args.worker))
    collect(args.selection.resolve(), args.output.resolve(), args.seconds, args.memory_mib,
            args.archive_mib, args.expanded_mib, args.artifact_mib)


if __name__ == '__main__':
    main()
