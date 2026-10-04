"""Known-answer tests for the exact ITS MCC wrapper, each in the campaign cgroup."""
import json
from pathlib import Path
import sys
import hashlib

F = Path(__file__).resolve().parent
ROOT = F.parents[2]
sys.path.insert(0, str(F.parent / 'runner-source/scripts'))
from linux_runner import run
from process_runner import workspace_workloads


def model(initial=1, read=False):
    return '<pnml xmlns="http://www.pnml.org/version-2009/grammar/pnml"><net id="net" type="http://www.pnml.org/version-2009/grammar/ptnet"><page id="page">' + f'<place id="p"><name><text>p</text></name><initialMarking><text>{initial}</text></initialMarking></place><place id="q"><name><text>q</text></name><initialMarking><text>0</text></initialMarking></place><transition id="t"><name><text>t</text></name></transition><arc id="a" source="p" target="t"><inscription><text>{2 if read else 1}</text></inscription></arc><arc id="b" source="t" target="q"/>' + ('<arc id="c" source="t" target="p"><inscription><text>2</text></inscription></arc>' if read else '') + '</page></net></pnml>'


def c(number):
    return f'<integer-constant>{number}</integer-constant>'


def p(name):
    return f'<tokens-count><place>{name}</place></tokens-count>'


def prop(name, kind, expression):
    outer, inner = ('exists-path', 'finally') if kind == 'EF' else ('all-paths', 'globally')
    return f'<property><id>{name}</id><description>qualification</description><formula><{outer}><{inner}>{expression}</{inner}></{outer}></formula></property>'


def main():
    assert not workspace_workloads(ROOT)
    folder = F / 'native-verified-cases'
    folder.mkdir()
    cases = [
        ('ef-true', 'EF', f'<integer-le>{c(1)}{p("q")}</integer-le>', True, model()),
        ('ef-false', 'EF', f'<integer-le>{c(2)}{p("q")}</integer-le>', False, model()),
        ('ag-true', 'AG', f'<integer-le>{c(0)}{p("q")}</integer-le>', True, model()),
        ('ag-false', 'AG', f'<integer-le>{c(1)}{p("q")}</integer-le>', False, model()),
        ('eq-true', 'EF', f'<integer-eq>{c(1)}{p("q")}</integer-eq>', True, model()),
        ('eq-false', 'EF', f'<integer-eq>{c(2)}{p("q")}</integer-eq>', False, model()),
        ('signed-true', 'EF', f'<integer-le>{c(1)}<sum>{p("q")}<product>{c(-1)}{p("p")}</product></sum></integer-le>', True, model()),
        ('signed-false', 'AG', f'<integer-le>{c(0)}<sum>{p("q")}<product>{c(-1)}{p("p")}</product></sum></integer-le>', False, model()),
        ('read-enabled', 'EF', f'<integer-le>{c(1)}{p("q")}</integer-le>', True, model(2, True)),
        ('read-disabled', 'EF', f'<integer-le>{c(1)}{p("q")}</integer-le>', False, model(1, True)),
        ('overflow-constant', 'EF', f'<integer-le>{c(2147483648)}{p("q")}</integer-le>', None, model()),
        ('overflow-expression', 'EF', f'<integer-le><sum>{c(2147483647)}{c(1)}</sum>{p("q")}</integer-le>', None, model()),
        ('overflow-marking', 'EF', f'<integer-le>{c(1)}{p("q")}</integer-le>', None, model(2147483648)),
    ]
    rows = []
    for name, kind, expression, expected, pnml in cases:
        case = folder / name
        case.mkdir()
        (case / 'model.pnml').write_text(pnml)
        xml = '<property-set>' + prop('distractor', 'EF', f'<integer-le>{c(999)}{p("q")}</integer-le>') + prop(name, kind, expression) + '</property-set>'
        (case / 'properties.xml').write_text(xml)
        cmd = [str(ROOT / 'vendor/venv/bin/python'), str(F.parent / 'runner-source/scripts/its_original.py'), '--runtime-config', str(F / 'runtime-native-config.json'), '--pnml', str(case / 'model.pnml'), '--xml', str(case / 'properties.xml'), '--property-id', name, '--artifacts', str(case / 'artifacts'), '--seconds', '5']
        wall, code, timeout, usage = run(cmd, ROOT, 5, case / 'runner.log', 2**31, cpus=[8], perf=True)
        response = json.loads((case / 'artifacts/result.json').read_text()) if (case / 'artifacts/result.json').exists() else None
        passed = code == 0 and not timeout and wall <= 5 and response is not None and response['property_truth'] is expected
        passed = passed and (bool(response['capability_failures']) if expected is None else response['tool_exit_code'] == 0 and not response['errors'])
        row = dict(name=name, expected=expected, passed=bool(passed), wall_seconds=wall, exit_code=code, outer_timeout=timeout, resources=usage, command=cmd, response=response)
        rows.append(row)
        (F / 'native-verified-qualification-rows.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps(dict(name=name,passed=bool(passed),wall_seconds=wall,response=response)),flush=True)
    assert not workspace_workloads(ROOT)
    result = dict(status='passed' if all(r['passed'] for r in rows) else 'failed', tests=len(rows), failures=[r['name'] for r in rows if not r['passed']], scope='Known-answer original EF/AG, equality, signed product, weighted ordinary read arcs, multiproperty isolation, and conservative signed-32-bit input rejection', rows_sha256=hashlib.sha256((F / 'native-verified-qualification-rows.json').read_bytes()).hexdigest())
    (F / 'native-verified-qualification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
