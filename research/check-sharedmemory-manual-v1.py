"""Propose manual answers, then check original inputs and each definitive branch.

This is a diagnostic using model names, not a solver or a benchmark result.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'results/runner-phase-pair-v1/source/scripts'
sys.path.insert(0, str(RUNNER))
from process_runner import run, workspace_workloads

CORPUS = ROOT / 'research/application-ladder-qualification-v1/stage-300'
OUT = ROOT / 'results/manual-sharedmemory-v1'
BINARY = ROOT / 'results/solver-pair-ablation-v1/vass-reach'
MEMORY = 2048 * 1024**2


def sha(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def save(p, value):
    with p.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def unknown():
    return dict(verdict='unknown', method='manual-diagnostic', reason='No certificate proposed for this branch', states=0, trace=[], marking=None)


def main():
    assert read(ROOT / 'research/pair-ablation-full-v1-terminal.json')['exit_code'] == 0
    assert not workspace_workloads(ROOT)
    assert not OUT.exists()
    queries = [q for q in read(CORPUS / 'manifest.json')['queries'] if q['name'].startswith('SharedMemory-')]
    assert len(queries) == 2
    pins = {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)), str(BINARY.relative_to(ROOT)): sha(BINARY)}
    for name, digest in read(RUNNER.parent.parent / 'files-sha256.json').items():
        p = RUNNER.parent / name
        assert sha(p) == digest
        pins[str(p.relative_to(ROOT))] = digest
    for q in queries:
        for field in ['pnml', 'xml']:
            p = (CORPUS / q[field]).resolve()
            assert sha(p) == q[field + '_sha256']
            pins[str(p.relative_to(ROOT))] = sha(p)
        for b in q['branches']:
            p = (CORPUS / b['path']).resolve()
            assert sha(p) == b['sha256']
            pins[str(p.relative_to(ROOT))] = sha(p)
    OUT.mkdir()
    save(OUT / 'plan.json', dict(scope='Manual diagnostic; no discovery-performance claim. Check original PNML/XML and every definitive branch.', seconds=60, memory_bytes=MEMORY, file_sha256=pins, queries=[q['name'] for q in queries]))
    receipts = []
    for q in queries:
        attempts = []
        positive = q['name'].endswith('RC03')
        for index, branch in enumerate(q['branches']):
            p = read(CORPUS / branch['path'])
            answer = unknown()
            if positive and index == 3:
                trace = [t for t, tr in enumerate(p['transitions']) if tr['name'].startswith('Req_Ext_Acc_')]
                assert len(trace) == 200
                marking = p['initial'][:]
                for t in trace:
                    for place, weight in p['transitions'][t]['pre']:
                        marking[place] -= weight
                    for place, weight in p['transitions'][t]['post']:
                        marking[place] += weight
                answer.update(verdict='reachable', reason='Manual proposal: request external access in every initially active process', trace=trace, marking=marking)
            elif not positive:
                n = len(p['places'])
                assert not any(c['equality'] for c in p['target'])
                multipliers = [[i, '1'] for i, name in enumerate(p['places']) if name.startswith('Ext_Mem_Acc_')]
                multipliers += [[n, '1'], [n + 2, '1']]
                answer.update(verdict='unreachable', reason='Manual proposal: combine target rows0and2 with external-access nonnegativity', proof=dict(kind='sparse-farkas-v1', multipliers=multipliers))
            attempts.append(dict(branch=index, outcome=answer))
            if answer['verdict'] != 'unknown':
                branch_answer = OUT / f"{q['name']}.branch-{index}.json"
                save(branch_answer, answer)
                command = [str(BINARY), '--json', str(CORPUS / branch['path']), '--verify', str(branch_answer), '--seconds', '60']
                log = OUT / f"{q['name']}.branch-{index}.rust-check.log"
                wall, code, expired, resources = run(command, ROOT, 60, log, memory_bytes=MEMORY)
                receipt = dict(query=q['name'], branch=index, command=command, wall_seconds=wall, exit_code=code, timeout=expired, resources=resources, scope='Certificate checking only, not solver discovery timing')
                receipts.append(receipt)
                save(OUT / f"{q['name']}.branch-{index}.rust-check.json", receipt)
                assert code == 0 and not expired and not resources['memory_limit_exceeded']
        verdict = 'reachable' if positive else 'unreachable'
        summary = dict(kind='original-property-v1', property_id=q['property_id'], property_kind=q['kind'], branch_count=len(q['branches']), verdict=verdict, property_truth=False, deadline_exceeded=False, parse_seconds=0, solve_seconds=0, attempts=attempts, reason='Manually proposed answers. Zero timing fields are schema placeholders, not measurements.')
        answer_path = OUT / f"{q['name']}.original-property.json"
        save(answer_path, summary)
        request = dict(query=q, corpus=str(CORPUS), artifacts=str(OUT), log=str(answer_path), mode='rust-original-v1', outer_timeout=False, exit_code=0, memory_bytes=MEMORY, response_bytes=64*1024**2, dag_check_max_work=200000000)
        request_path = OUT / f"{q['name']}.request.json"
        response_path = OUT / f"{q['name']}.response.json"
        save(request_path, request)
        command = [sys.executable, str(RUNNER / 'bounded_validation.py'), '--request', str(request_path), '--response', str(response_path)]
        wall, code, expired, resources = run(command, ROOT, 60, OUT / f"{q['name']}.python-check.log", memory_bytes=MEMORY)
        receipt = dict(query=q['name'], command=command, wall_seconds=wall, exit_code=code, timeout=expired, resources=resources, scope='Independent original-input translation and checking only')
        receipts.append(receipt)
        save(OUT / f"{q['name']}.python-check.json", receipt)
        assert code == 0 and not expired and not resources['memory_limit_exceeded']
        response = read(response_path)
        assert response['verdict'] == verdict and response['property_truth'] is False
        assert response['translation_check'] == 'independent-original-input-equals-all-canonical-branches'
        expected = ['none', 'none', 'none', 'python-witness'] if positive else ['python-sparse-farkas']*2
        assert response['independent_checks'] == expected
        print(q['name'], response['verdict'], response['independent_checks'], flush=True)
    assert all(sha(ROOT / name) == digest for name, digest in pins.items())
    save(OUT / 'verification.json', dict(status='passed', queries=2, definitive_branches=3, receipts=receipts, artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file()}, scope='Manual diagnostic establishes truth, not an automatic solver result or performance improvement. Both original properties are false.'))


if __name__ == '__main__':
    main()
