"""Preserve historical cohorts and add completed, audited general-solver evidence."""
from collections import Counter
import runpy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
helpers = runpy.run_path(str(ROOT / 'research/build-hardness-catalog-v5.py'))
read, audited, verify, digest = (helpers[k] for k in ('read', 'audited', 'verify', 'digest'))
SOURCES, VERIFIED = (helpers[k] for k in ('SOURCES', 'VERIFIED'))


def main():
    result = read('benchmarks/development-hardness-catalog-v5.json')
    verify(result['source_sha256'])
    SOURCES.update(result['source_sha256'])
    SOURCES['research/build-hardness-catalog-v6.py'] = digest('research/build-hardness-catalog-v6.py')
    full = audited('research/application-walk-full-v1/audit.json')
    assert full['rows'] == 3280 and not full['audit_issues']
    assert full['classification']['full']['definitive_by_method'] == {
        'native-walk':632, 'native-batched':615, 'native-frozen':614,
        'verifypn-default':603, 'smpt-full-portable':394}
    paired = read('research/application-walk-full-v1/paired-coverage.json')
    instructions = read('research/application-walk-full-v1/instruction-summary.json')
    assert instructions['audit_sha256'] == digest('research/application-walk-full-v1/audit.json')
    pair = audited('research/pair-ablation-full-v1-audit.json')
    selected_pair = audited('research/phase-pair-survivors-v1-audit.json')
    guided = audited('research/guided-walk-gap-v1-audit.json')
    capacity = audited('research/capacity-combinations-gap-v1-audit.json')
    raw = audited('research/raw-encoded-work-cohorts-v1-verification.json')
    transfer = audited('research/transfer-raw-encoded-work-v1-verification.json')
    manual = audited('results/manual-sharedmemory-v1/verification.json')
    gap_plan = read('research/capacity-combinations-gap-v1-plan.json')
    assert pair['rows'] == 1312 and pair['checked_definitive_rows'] == 4
    assert guided['rows'] == 24 and guided['checked_definitive_rows'] == 3
    assert capacity['rows'] == 16 and capacity['checked_definitive_rows'] == 2
    assert raw['rows'] == 28 and not raw['unresolved']
    assert transfer['source_slots'] == 12 and len(transfer['unresolved']) == len(transfer['unavailable']) == 3
    runs = [json.loads(s) for s in (ROOT/'results/linux-application-walk-full-v1/runs.jsonl').read_text().splitlines()]
    unknowns = sorted(r['query'] for r in runs if r['method']=='native-walk' and r['collection_status']=='imported' and r['verdict'] not in ['reachable','unreachable'])
    assert unknowns == sorted(gap_plan['queries']) and len(unknowns) == 8
    def compact(a):
        return {k:v for k,v in a.items() if k not in ['artifact_sha256', 'details']}
    result.update(format='pvass-development-hardness-catalog-v6', supersedes='benchmarks/development-hardness-catalog-v5.json')
    result['contribution_scope'] = 'General Petri-net reachability solver; serializability is an application. No novelty, publication readiness or general superiority established.'
    result['ordinary_full_walk_comparison'] = {
        'summary':full['classification']['full'], 'rows':full['rows'],
        'exact_ordered_branch_representatives':full['exact_ordered_branch_representatives'],
        'warnings':len(full['warnings']), 'paired_coverage':paired,
        'native_walk_unknowns':unknowns,
        'limits':{'seconds':5,'memory_mib':2048,'cpu':8,'repeat':1,'checker_seconds_separate':60},
        'instruction_comparison':instructions,
        'finding':'Coverage gain costs work on jointly solved cases. Native answers independently checked; external answers tool-reported. Full656/640/16denominators and duplicate slots retained.'}
    result['selected_walk_gap_experiments']['followup'] = 'Full Linux comparison now complete: see ordinary_full_walk_comparison. Historical selected pilots retained unchanged.'
    result['phase_pair_experiments'] = {
        'full':compact(pair), 'selected_30s':compact(selected_pair),
        'finding':'Phase-pair4/640 versus uniform0/640 at5s locally. Selected30s run checks TokenRing30/40RC09. Restricted discovery and relation cap limit applicability; not a broad improvement or novelty claim.'}
    result['guided_walk_experiment'] = {
        **compact(guided), 'decision':'Do not promote: all three standalone methods solve the same one of eight gaps; guided search gains no coverage.'}
    result['capacity_combinations_experiment'] = {
        **compact(capacity),
        'decision':'Keep opt-in pending full-cohort regression/cost measurement. Automatically checks both negative branches of SharedMemory200RC04; one new capability with existing Farkas proof rule.'}
    result['manual_sharedmemory'] = {
        'source':'results/manual-sharedmemory-v1/verification.json', 'scope':manual['scope'],
        'current_status':'RC03 also automatically solved in full Linux native-walk comparison. RC04 now automatically solved by local capacity pilot. Manual proofs are not benchmark timings.'}
    result['raw_ser']['encoded_work_regression'] = compact(raw)
    result['raw_ser']['compressed_control_regression']['followup'] = 'Historical25/27result retained. Encoded-word accounting repair restores27/27available slots; see encoded_work_regression.'
    result['transfer_family']['encoded_work_followup'] = compact(transfer)
    result['transfer_family']['status'] = 'Six checked positive answers, three strict solver timeouts, three unavailable exports. Work accounting repair adds no transfer coverage.'
    result['pending_historical_ordinary_comparison'] = {
        'plan':'research/hard-survivors-current-v2/plan.json', 'expected_rows':40,
        'parent_denominators':[620,69,8], 'seconds':300,
        'status':'Running at catalog creation; no current-hardness conclusion from partial rows.'}
    result['reservation'] = 'All22reserved families excluded; only named development evidence and recorded artifacts read.'
    result['source_sha256'] = dict(sorted(SOURCES.items()))
    result['verified_evidence_sha256'] = dict(sorted(VERIFIED.items()))
    result['hash_verification_scope'] = 'Rehashed v5 sources and each new passed audit artifact closure; reconciles saved checks, without rerunning solvers or proofs.'
    output = ROOT/'benchmarks/development-hardness-catalog-v6.json'
    with output.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps({'status':'passed','source_files':len(SOURCES),'verified_evidence_files':len(VERIFIED),'catalog':str(output)}))

if __name__ == '__main__':
    main()
