"""Check the actual four-tool harness on known EF/AG answers and SMPT components."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def run(plan, command):
    from linux_runner import run as bounded_run
    from process_runner import workspace_workloads
    import smpt_import as imp
    assert not workspace_workloads(ROOT)
    corpus = ROOT / 'benchmarks/competitive-capability-20261004'
    output = ROOT / 'results/competitive-capability-20261004'
    assert not corpus.exists() and not output.exists()
    corpus.mkdir()
    model = corpus / 'model.pnml'
    model.write_text('''<pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml"><net id="smoke" type="http://www.pnml.org/version-2009/grammar/ptnet"><page id="page"><place id="p"><name><text>p</text></name><initialMarking><text>1</text></initialMarking></place><place id="q"><name><text>q</text></name><initialMarking><text>0</text></initialMarking></place><transition id="move"><name><text>move</text></name></transition><arc id="a" source="p" target="move"/><arc id="b" source="move" target="q"/></page></net></pnml>''')
    problem = imp.pnml(model)
    records, expected = [], {}
    for slot, (kind, bound, truth) in enumerate([('EF', 1, True), ('EF', 2, False), ('AG', 0, True), ('AG', 1, False)]):
        name = f'{kind}-{bound}'
        folder = corpus / name
        folder.mkdir()
        outer, inner = ('exists-path', 'finally') if kind == 'EF' else ('all-paths', 'globally')
        xml = folder / 'original.xml'
        xml.write_text(f'<property-set><property><id>{name}</id><description>capability</description><formula><{outer}><{inner}><integer-le><integer-constant>{bound}</integer-constant><tokens-count><place>q</place></tokens-count></integer-le></{inner}></{outer}></formula></property></property-set>')
        prop = imp.properties(xml, problem)[0]
        branches = []
        for index, target in enumerate(prop.pop('targets')):
            path = folder / f'branch-{index}.json'
            path.write_text(json.dumps(dict(problem, target=target)))
            branches.append(dict(path=str(path.relative_to(corpus)), sha256=sha(path)))
        net, translated = folder / 'model.net', folder / 'property.xml'
        net.write_text(imp.tina(problem))
        translated.write_text(imp.translated_xml(xml, problem['places']))
        record = dict(name=name, suite='synthetic-capability', instance='one-token-move',
                      family='Synthetic', status='imported', planned=True, observed=True,
                      property_slot=slot, branches=branches, places=2, transitions=1, **prop)
        for field, path in [('pnml', model), ('xml', xml), ('net', net), ('property', translated)]:
            record[field] = str(path.relative_to(corpus))
            record[field + '_sha256'] = sha(path)
        records.append(record)
        expected[name] = truth
    (corpus / 'manifest.json').write_text(json.dumps(dict(format='synthetic-capability-v1', queries=records), indent=2))
    cmd = command(plan, plan['blocks'][0])
    for flag, value in [('--corpus', str(corpus)), ('--output', str(output))]:
        cmd[cmd.index(flag) + 1] = value
    with (F / 'capability-plan.json').open('x') as out:
        json.dump(dict(plan_sha256=sha(F / 'plan.json'), command=cmd, expected=expected,
                       manifest_sha256=sha(corpus / 'manifest.json')), out, indent=2)
    with (F / 'capability-harness.log').open('x') as log:
        result = subprocess.run(cmd, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                stdout=log, stderr=subprocess.STDOUT)
    result.check_returncode()
    rows = [json.loads(line) for line in (output / 'runs.jsonl').read_text().splitlines()]
    assert len(rows) == 16
    assert {(r['query'], r['method']) for r in rows} == {(q, m) for q in expected for m in plan['methods']}
    limitations = []
    for row in rows:
        documented_timeout = (row['method'] == 'its-mcc' and row['query'] == 'EF-2'
                              and row['verdict'] == 'unknown' and row['property_truth'] is None
                              and row['outer_timeout'])
        if documented_timeout:
            limitations.append(dict(query=row['query'], method=row['method'],
                                     reason='Known ITS negative case does not exit within five seconds; correctly retained as unknown.'))
        else:
            assert row['property_truth'] is expected[row['query']], row
            assert row['exit_code'] == 0 and not row['outer_timeout'] and row['wall_seconds'] <= 5, row
        usage = row['resources']
        assert usage['runner'] == 'linux-systemd-user' and usage['cpus'] == [8]
        assert usage['memory_limit_bytes'] == 2**31 and not usage.get('memory_limit_exceeded')
        assert usage['perf_enabled']
        if not documented_timeout:
            assert usage['perf_counters']['instructions:u']['value'] > 0
        if row['method'] == 'native-excess':
            assert row['independent_checks'] and row['validation']['exit_code'] == 0
    folder = F / 'components'
    folder.mkdir()
    os.environ['PATH'] = ':'.join(str(ROOT / p) for p in [plan['minizinc_tool_bin'], 'vendor/venv/bin',
        'vendor/tina-linux/tina-4.0.0/bin', 'vendor/4ti2-install/bin']) + ':' + os.environ['PATH']
    os.environ['PYTHONPATH'] = str(ROOT / 'vendor/SMPT-portable')
    component_rows = []
    for method, labels in [('SMT', ['sat', 'unsat']), ('CP', ['sat', 'unsat']), ('WALK', ['sat'])]:
        for label in labels:
            log = folder / f'{method}-{label}.log'
            xml = ROOT / f'research/smpt-minizinc-repair-v1/smpt-cp-{label}.xml'
            cmd = [str(ROOT / 'vendor/venv/bin/python'), '-m', 'smpt', '--net',
                   str(ROOT / 'research/smpt-minizinc-repair-v1/model.net'), '--xml', str(xml),
                   '--methods', method, '--timeout', '5', '--show-techniques', '--show-model', '--debug']
            if method != 'WALK':
                cmd.append('--auto-reduce')
            wall, code, expired, usage = bounded_run(cmd, ROOT / 'vendor/SMPT-portable', 5, log, 2**31, cpus=[8], perf=True)
            text = log.read_text()
            truth = 'TRUE' if label == 'sat' else 'FALSE'
            passed = code == 0 and not expired and wall <= 5 and f'FORMULA smpt-cp-{label} {truth}' in text
            passed = passed and not re.search(r'Traceback|command not found|No such file or directory', text)
            if method == 'CP':
                passed = passed and 'CONSTRAINT_PROGRAMMING' in text and 'solve satisfy;' in text
            if method == 'WALK':
                passed = passed and 'WALK' in text
            component_rows.append(dict(method=method, label=label, passed=bool(passed), command=cmd,
                                       wall_seconds=wall, exit_code=code, outer_timeout=expired,
                                       resources=usage, log_sha256=sha(log)))
            (folder / 'rows.json').write_text(json.dumps(component_rows, indent=2))
            assert passed, component_rows[-1]
    assert not workspace_workloads(ROOT)
    receipt = dict(status='passed', plan_sha256=sha(F / 'plan.json'), methods=plan['methods'],
                   harness_rows=len(rows), component_rows=component_rows,
                   known_limitations=limitations,
                   its_qualification_sha256=sha(ROOT / plan['its_qualification']),
                   runs_sha256=sha(output / 'runs.jsonl'), environment_sha256=sha(output / 'environment.json'),
                   scope='Known-answer configuration checks; no competitive result.')
    with (F / 'capability.json').open('x') as out:
        json.dump(receipt, out, indent=2)
    print(json.dumps(dict(status='passed', harness_rows=len(rows), component_rows=len(component_rows))), flush=True)
