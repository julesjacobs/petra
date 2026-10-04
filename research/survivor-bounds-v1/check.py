"""Check total-token bounds on the four models in the previous survivor cohort."""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from smpt_import import pnml
from bounded_token_cut_checker import verify_place_bounds


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    require(__debug__, 'The existing independent checker requires assertions enabled')
    corpus = ROOT / 'benchmarks/general-development-v3'
    manifest_path = corpus / 'manifest.json'
    plan = json.loads((ROOT / 'research/portfolio-reduced-linux-v1/plan.json').read_text())
    require(sha(manifest_path) == plan['manifest_sha256'], 'Manifest identity changed')
    selection_path = ROOT / 'research/portfolio-reduced-linux-v1/summary.json'
    selection = json.loads(selection_path.read_text())
    queries = json.loads(manifest_path.read_text())['queries']
    selected = {q['name']: q for q in queries if q['name'] in selection['all_unresolved']}
    require(len(selected) == 41, 'Unexpected original survivor population')
    instances = sorted({q['instance'] for q in selected.values()})
    records = []
    for instance in instances:
        members = [q for q in selected.values() if q['instance'] == instance]
        q = members[0]
        source = corpus / q['pnml']
        require(all(m['pnml'] == q['pnml'] and m['pnml_sha256'] == q['pnml_sha256']
                    for m in members), 'Inconsistent original model identity')
        require(sha(source) == q['pnml_sha256'], 'Original PNML identity changed')
        problem = pnml(source)
        branch = q['branches'][0]
        canonical_path = corpus / branch['path']
        require(sha(canonical_path) == branch['sha256'], 'Canonical input identity changed')
        canonical = json.loads(canonical_path.read_text())
        for field in ['places', 'initial', 'transitions']:
            require(json.loads(json.dumps(problem[field])) == canonical[field],
                    'Original and canonical nets differ: ' + field)

        changes = Counter(sum(w for _, w in t['post']) - sum(w for _, w in t['pre'])
                          for t in problem['transitions'])
        require(all(change <= 0 for change in changes), 'Total tokens can increase')
        mass = sum(problem['initial'])
        certificate = {'kind': 'place-bounds-v1', 'potentials': [
            {'weights': [[i, '1'] for i in range(len(problem['places']))]}]}
        bounds = verify_place_bounds(problem, certificate)
        require(bounds == [mass] * len(problem['places']), 'Independent bound mismatch')
        certificate_path = OUT / (instance + '.certificate.json')
        certificate_path.write_text(json.dumps(certificate, indent=2) + '\n')
        records.append(dict(
            instance=instance, previous_unresolved_properties=len(members),
            original_pnml=str(source.relative_to(ROOT)), pnml_sha256=sha(source),
            canonical_input=str(canonical_path.relative_to(ROOT)),
            canonical_sha256=sha(canonical_path), places=len(problem['places']),
            transitions=len(problem['transitions']), initial_total=mass,
            max_initial_place=max(problem['initial']), transition_total_changes=dict(changes),
            certified_uniform_place_bound=mass,
            marking_count_upper_bound=str(math.comb(len(problem['places']) + mass, mass)),
            certificate=certificate_path.name, certificate_sha256=sha(certificate_path)))
        print(instance, 'checked bound', mass, flush=True)
    sources = [Path(__file__), ROOT / 'scripts/smpt_import.py',
               ROOT / 'scripts/bounded_token_cut_checker.py',
               ROOT / 'scripts/token_moment_checker.py', ROOT / 'scripts/token_cut_checker.py']
    result = dict(status='passed', scope='Structural bounds on original nets; no property verdict or timing result.',
                  population='41 all-method unknown properties from the earlier single five-second screen',
                  selection_sha256=sha(selection_path), manifest_sha256=sha(manifest_path),
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources}, models=records)
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
