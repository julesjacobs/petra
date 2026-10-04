"""Narrow provenance amendment; rerun the frozen auditor without editing it."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import tarfile

F=Path(__file__).resolve().parent
ROOT=F.parents[1]
STATUS='passed-with-provenance-amendment'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    evidence={}
    def read(path):
        evidence[str(path.relative_to(ROOT))]=sha(path)
        return json.loads(path.read_text())
    pins=read(F/'analysis-v2-sha256.json')
    for name,digest in pins.items():assert sha(ROOT/name)==digest,name
    amendment=read(F/'analysis-amendment-v2.json')
    for name,digest in amendment['evidence_sha256'].items():assert sha(ROOT/name)==digest,name
    original=read(F/'audit.json');plan=read(F/'plan.json');execution=read(F/'execution.json')
    assert original['status']=='failed' and original['issues']==amendment['permitted_original_issues']
    assert sha(F/'audit.py')==amendment['frozen_auditor_sha256']
    spec=importlib.util.spec_from_file_location('frozen_audit',F/'audit.py')
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    repeated=frozen.run()
    assert repeated['status']=='failed' and repeated['issues']==amendment['permitted_original_issues'],repeated['issues']
    assert repeated['artifact_sha256']==original['artifact_sha256'],'Frozen audit evidence changed'
    assert repeated['blocks']==original['blocks'],'Frozen block audit changed'
    capability=read(F/'capability.json')
    capability_environment=ROOT/'results/competitive-capability-20261004/environment.json'
    env=read(capability_environment)
    assert execution['plan_sha256']==sha(F/'plan.json') and execution['capability_sha256']==sha(F/'capability.json')
    assert capability['status']=='passed' and capability['plan_sha256']==sha(F/'plan.json')
    assert capability['environment_sha256']==sha(capability_environment)
    assert env['tools']['z3']==amendment['z3_observation']
    relative_z3=amendment['omitted_required_file']
    assert relative_z3 not in plan['required_file_sha256']
    assert relative_z3 not in read(F/'inherited-runtime-sha256.json')
    collection=read(F/'qualification-collection.json')
    paths=['research/competitive-linux-20261004/capability.json',
           'research/competitive-linux-20261004/capability-plan.json',
           'results/competitive-capability-20261004/environment.json']
    for name in paths:assert collection['files_sha256'][name]==sha(ROOT/name)
    archive=F/'qualification-evidence.tar.gz'
    assert sha(archive)==collection['archive_sha256'];evidence[str(archive.relative_to(ROOT))]=sha(archive)
    found=set()
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            name=member.name.removeprefix('./')
            if name in paths:
                assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==collection['files_sha256'][name]
                found.add(name)
    assert found==set(paths)
    observations=[];rows={}
    campaign=read(F/'campaign-collection.json')
    for block in plan['blocks']:
        terminal=read(F/(block['name']+'-terminal.json'))
        path=ROOT/block['output']/'environment.json';current=read(path);name=str(path.relative_to(ROOT))
        assert terminal['artifact_sha256'][name]==sha(path)==campaign['files_sha256'][name]
        assert current['tools']['z3']==amendment['z3_observation']
        observations.append(dict(block=block['name'],environment=name,environment_sha256=sha(path),z3=current['tools']['z3'],
                                 loadavg=current['linux_host']['loadavg']))
        count=re.search(r'^CPU\(s\):\s*(\d+)\s*$',current['linux_host']['lscpu'],re.M)
        assert count and int(count[1])==32
        raw=ROOT/block['output']/'runs.jsonl'
        rows[block['name']]={(r['query'],r['method']):r for r in map(json.loads,raw.read_text().splitlines())}
    ratios={}
    for method in plan['methods']:
        common=sorted(q for q,m in rows['repeat1'] if m==method and all(rows[b][q,m]['verdict'] in ('reachable','unreachable') for b in rows))
        values=[rows['repeat1'][q,method]['wall_seconds']/rows['repeat2'][q,method]['wall_seconds'] for q in common]
        ratios[method]=dict(common_solved_count=len(common),queries=common,
            geometric_mean_repeat1_over_repeat2=math.exp(statistics.mean(map(math.log,values))),
            scope='Conditioned on this method solving the query in both repetitions; descriptive wall-time variation.')
    contention=dict(classification='contended-pilot',idle_host_objective_met=False,logical_cpus=32,
        recorded_loadavg_by_block={o['block']:o['loadavg'] for o in observations},within_tool_wall_ratios=ratios,
        caveat='The recorded one-minute load averages were 34.37 and 25.06 on 32 logical CPUs. Each tool was 1.41–1.82 times slower in repeat 1 on its own common-solved queries. This is a contended pilot, not an idle-host measurement; CPU affinity and the workspace workload gate did not establish host-wide isolation. Timings and deadline-sensitive coverage should not be treated as an uncontended comparison. The provenance amendment does not repair the idle-host launch objective or certify idle-host protocol conformance.')
    assert [float(o['loadavg'].split()[0]) for o in observations]==[34.37,25.06]
    result=dict(repeated,status=STATUS,issues=[],original_audit_status=original['status'],
        original_audit_sha256=sha(F/'audit.json'),original_issues=original['issues'],
        amendment_sha256=sha(F/'analysis-amendment-v2.json'),amendment=amendment,
        supplemental_provenance_evidence=evidence,z3_observations=observations,
        host_contention=contention,amended_auditor_sha256=sha(Path(__file__)),
        scope='The unchanged frozen audit passes every check except the two explicitly preserved Z3 pin omissions. Their recorded pre-launch identity is corroborated by the launch-bound capability chain. This analysis-only amendment does not retroactively enforce that omitted pin. Contended pilot; this status certifies saved-evidence consistency under the provenance amendment, not idle-host protocol conformance. Native checks inspected, external answers tool-reported.')
    with (F/'audit-v2.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    with (F/'host-contention.json').open('x') as out:json.dump(contention,out,indent=2);out.write('\n')
    print(json.dumps(dict(status=STATUS,original_issues=original['issues'],blocks=result['blocks'],host_classification='contended-pilot')))


if __name__=='__main__':main()
