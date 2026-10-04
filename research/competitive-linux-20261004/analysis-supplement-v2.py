"""Post-collection independent admission and aggregate checks; no tool execution."""
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from collections import Counter, defaultdict

F = Path(__file__).resolve().parent
ROOT = F.parents[1]
REMOTE = '/home/jules/experiments/pvass-publication'
DEFINITIVE = {'reachable','unreachable'}
MAX_BYTES = 64*1024**2
FAILURE = re.compile(
    r'Traceback \(most recent call last\):|\b(?:[A-Za-z]+Exception|Exception in thread)\b'
    r'|\bCANNOT_COMPUTE\b|\boverflow\b|\bunsupported\b|\bnot supported\b'
    r'|command not found|No such file or directory|bad command line'
    r'|\b(?:unknown|unrecognized|invalid) (?:option|argument)\b'
    r'|(?:^|\s)(?:ERROR|FATAL)(?:\s*[:!]|\s*$)|error: 4ti2 failed'
    r'|\b(?:OutOfMemoryError|StackOverflowError|LinkageError|AssertionError)\b',re.I)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def local_path(path):
    prefix=REMOTE+'/'
    assert path.startswith(prefix),path
    return ROOT/path[len(prefix):]


def parse_formulas(text, query, code, expired, wall):
    lines=text.splitlines()
    key=re.escape(query['property_id'])
    formulas=[line for line in lines if re.match(r'^FORMULA '+key+r'(?:\s|$)',line)]
    pattern=re.compile(r'^FORMULA '+key+r' (TRUE|FALSE)(?:\s+TECHNIQUES(?:\s+.*)?)?\s*$')
    parsed=[pattern.fullmatch(line) for line in formulas]
    results=[m[1] for m in parsed if m is not None]
    diagnostics=sorted({line for line in lines if FAILURE.search(line)})
    reasons=[]
    if expired: reasons.append('outer-timeout')
    if not math.isfinite(wall) or wall>5: reasons.append('wall-budget')
    if code!=0: reasons.append('nonzero-exit')
    if diagnostics: reasons.append('diagnostic-failure')
    if query['kind'] not in ('EF','AG'): reasons.append('unsupported-property-kind')
    if any(m is None for m in parsed): reasons.append('malformed-formula-result')
    if len(set(results))>1: reasons.append('conflicting-formula-results')
    if not results: reasons.append('missing-formula-result')
    observed=None
    if len(set(results))==1 and query['kind'] in ('EF','AG'):
        observed='reachable' if ((results[0]=='TRUE')==(query['kind']=='EF')) else 'unreachable'
    return dict(verdict=observed if not reasons else 'unknown',observed_verdict=observed,
                formula_output=formulas,observed_formula_results=results,
                capability_failures=diagnostics,
                subprocess_error=any(re.search(r'Traceback|Exception|\bERROR\b|\bFATAL\b',s,re.I) for s in diagnostics),
                admission_failures=reasons)


def admit(result,row):
    result=dict(result)
    reasons=list(result.get('admission_failures',[]))
    if row['outer_timeout']: reasons.append('outer-timeout')
    if not math.isfinite(row['wall_seconds']) or row['wall_seconds']>5: reasons.append('wall-budget')
    if row['exit_code']!=0: reasons.append('nonzero-exit')
    if result.get('subprocess_error') or result.get('capability_failures'): reasons.append('diagnostic-failure')
    if (row.get('resources') or {}).get('memory_limit_exceeded'): reasons.append('memory-limit')
    if result.get('verdict') not in DEFINITIVE|{'unknown'}: reasons.append('nondefinitive-failure')
    if reasons:
        result.setdefault('observed_verdict',result.get('verdict'))
        result['verdict']='unknown'
    result['admission_failures']=sorted(set(reasons))
    return result


def reconstruct_its(query,row,log,record,check):
    expected=dict(verdict='unknown')
    try:
        if log.stat().st_size>MAX_BYTES: raise ValueError('size')
        summary=json.loads(log.read_text())
        if not isinstance(summary,dict): raise ValueError('object')
        if summary.get('kind')!='its-original-v1': raise ValueError('kind')
        if summary.get('property_id')!=query['property_id'] or summary.get('property_kind')!=query['kind']: raise ValueError('query')
        for field in ('capability_failures','errors'):
            if type(summary.get(field)) is not list or not all(isinstance(s,str) for s in summary[field]): raise ValueError(field)
        if type(summary.get('timed_out')) is not bool: raise ValueError('timed_out')
        if summary.get('tool_exit_code') is not None and type(summary['tool_exit_code']) is not int: raise ValueError('exit_code')
        verdict=summary.get('verdict')
        if verdict not in DEFINITIVE|{'unknown'}: raise ValueError('verdict')
        truth=None if verdict=='unknown' else ((verdict=='reachable')==(query['kind']=='EF'))
        if summary.get('property_truth') is not truth: raise ValueError('polarity')
        for field in ('stage_seconds','tool_seconds','parse_seconds','total_seconds'):
            value=summary.get(field)
            if type(value) not in (int,float) or not math.isfinite(value) or value<0: raise ValueError(field)
        expected.update(verdict=verdict,observed_verdict=verdict,its_summary=summary,
                        capability_failures=list(summary['capability_failures']),
                        subprocess_error=bool(summary['errors'] or summary.get('error') or summary.get('subprocess_error')),
                        tool_exit_code=summary.get('tool_exit_code'))
        reasons=[]
        if summary.get('tool_exit_code')!=0: reasons.append('tool-nonzero-exit')
        if summary.get('timed_out'): reasons.append('tool-timeout')
        if summary['total_seconds']>5: reasons.append('wrapper-wall-budget')
        expected['admission_failures']=reasons
    except (OSError,ValueError,TypeError):
        expected['admission_failures']=['invalid-wrapper-result']
    artifacts=local_path(row['artifacts'])
    paths=sorted(p for p in artifacts.rglob('*') if p.is_file() and
                 (p.suffix.lower() in ('.log','.out','.err') or p.name in ('stdout','stderr')))
    # Historical read failure cannot be reenacted after transfer. The previously
    # hashed readable prefix and retained error justify unknown conservatively.
    read_failure='unreadable-underlying-tool-log' in row.get('admission_failures',[])
    if read_failure:
        check(bool(row.get('underlying_log_error')),'ITS read failure lacks saved reason')
        paths=[local_path(item['path']) for item in row.get('underlying_logs',[])]
        expected['admission_failures'].append('unreadable-underlying-tool-log')
    observed=[];contents=[];total=0
    for path in paths:
        check(path.is_relative_to(artifacts),'ITS log outside artifact directory')
        total+=path.stat().st_size
        if total>MAX_BYTES:
            expected['admission_failures'].append('underlying-log-size-limit')
            break
        data=path.read_bytes();record(path)
        text=data.decode('utf-8',errors='replace');contents.append(text)
        observed.append(dict(path=REMOTE+'/'+str(path.relative_to(ROOT)),sha256=sha(path),bytes=len(data)))
        failures=[s for s in text.splitlines() if FAILURE.search(s)]
        if failures: expected.setdefault('capability_failures',[]).extend(failures)
    check(observed==row.get('underlying_logs'),'ITS readable log inventory differs')
    if not observed: expected['admission_failures'].append('missing-underlying-tool-log')
    expired=(row.get('resources') or {}).get('systemd_result') in ('timeout','oom-kill')
    parsed=parse_formulas('\n'.join(contents),query,expected.get('tool_exit_code'),expired,row['wall_seconds'])
    expected['formula_output']=parsed['formula_output']
    expected['observed_formula_results']=parsed['observed_formula_results']
    expected['admission_failures'].extend(parsed['admission_failures'])
    if expected['verdict'] in DEFINITIVE and expected['verdict']!=parsed['verdict']:
        expected['admission_failures'].append('wrapper-tool-verdict-mismatch')
    return admit(expected,row),read_failure


def solved(row):
    return row['verdict'] in DEFINITIVE and type(row['property_truth']) is bool


def validation_time(row):
    if 'validation' not in row: return 0
    value=row['validation'].get('wall_seconds')
    assert type(value) in (int,float) and math.isfinite(value) and value>=0,'Missing or invalid validator duration'
    return value


def aggregate(names,methods,cases):
    names=sorted(names);blocks=list(cases)
    sets={m:[{q for q in names if solved(cases[b][q,m])} for b in blocks] for m in methods}
    result=dict(denominator=len(names),methods={},pairs={})
    for m in methods:
        rows=[cases[b][q,m] for b in blocks for q in names]
        solver=sum(row['wall_seconds'] for row in rows);checking=sum(validation_time(row) for row in rows)
        result['methods'][m]=dict(solved_by_repeat=list(map(len,sets[m])),stable=len(sets[m][0]&sets[m][1]),
            any_repeat=len(sets[m][0]|sets[m][1]),solver_wall_total_seconds=solver,
            validation_wall_total_seconds=checking,solver_plus_recorded_validation_seconds=solver+checking,
            solver_par2_mean_seconds=sum(row['wall_seconds'] if solved(row) else 10 for row in rows)/len(rows))
    for m in methods:
        if m=='native-excess':continue
        ours,theirs=sets['native-excess'],sets[m]
        gains=[ours[i]-theirs[i] for i in range(2)];losses=[theirs[i]-ours[i] for i in range(2)]
        common=ours[0]&ours[1]&theirs[0]&theirs[1]
        ratios=[[],[]]
        for q in sorted(common):
            for i in range(2):
                left=statistics.median(cases[b][q,m]['wall_seconds']+(validation_time(cases[b][q,m]) if i else 0) for b in blocks)
                right=statistics.median(cases[b][q,'native-excess']['wall_seconds']+(validation_time(cases[b][q,'native-excess']) if i else 0) for b in blocks)
                ratios[i].append(left/right)
        gm=lambda xs:math.exp(sum(map(math.log,xs))/len(xs)) if xs else None
        result['pairs'][m]=dict(gains_by_repeat=list(map(sorted,gains)),losses_by_repeat=list(map(sorted,losses)),
            stable_gains=sorted(gains[0]&gains[1]),stable_losses=sorted(losses[0]&losses[1]),
            common_solved=dict(denominator=len(common),queries=sorted(common),
                geometric_mean_competitor_over_candidate_solver=gm(ratios[0]),
                geometric_mean_competitor_over_candidate_with_recorded_validation=gm(ratios[1])))
    all_ever=set().union(*(x for values in sets.values() for x in values))
    result['never_solved_by_any_method']=sorted(set(names)-all_ever)
    result['stable_method_exclusive']={m:sorted((sets[m][0]&sets[m][1])-set().union(*(x for n in methods if n!=m for x in sets[n]))) for m in methods}
    return result


def main():
    issues=[];evidence={};admission_counts=Counter();demotions=[];rows_checked=0;read_failures=0
    def check(condition,message):
        if not condition:issues.append(message)
        return condition
    def record(path):
        evidence[str(path.relative_to(ROOT))]=sha(path)
    def read(path):
        record(path);return json.loads(path.read_text())
    def compare(expected,actual,path):
        if isinstance(expected,dict):
            for key,value in expected.items():
                check(key in actual,path+': missing '+key)
                if key in actual:compare(value,actual[key],path+'/'+key)
        elif type(expected) is float:
            check(type(actual) in (int,float) and math.isclose(expected,actual,rel_tol=1e-12,abs_tol=1e-9),path+': numeric mismatch')
        else:check(expected==actual,path+': mismatch')
    manifest_pins=read(F/'analysis-v2-sha256.json')
    for name,digest in manifest_pins.items():check(sha(ROOT/name)==digest,'Supplement source changed: '+name)
    plan=read(F/'plan.json');terminal=read(F/'terminal.json')
    assert terminal['plan_sha256']==sha(F/'plan.json') and terminal['exit_code']==0 and terminal['completed']==['repeat1','repeat2'],'Campaign not complete'
    original_audit=read(F/'audit-v2.json');summary=read(F/'summary.json')
    assert original_audit['status']=='passed-with-provenance-amendment' and not original_audit['issues'],'Main artifact audit must pass first'
    assert summary['status']=='two-complete-repeats-with-provenance-amendment' and summary['audit_sha256']==sha(F/'audit-v2.json'),'Summary identity differs'
    assert summary['plan_sha256']==sha(F/'plan.json'),'Summary plan differs'
    manifest=read(ROOT/plan['corpus']/'manifest.json');queries={q['name']:q for q in manifest['queries']}
    cases={}
    for block in plan['blocks']:
        output=ROOT/block['output'];block_terminal=read(F/(block['name']+'-terminal.json'))
        assert block_terminal['plan_sha256']==sha(F/'plan.json') and block_terminal['exit_code']==0 and block_terminal['rows']==1472,'Incomplete block'
        raw=output/'runs.jsonl';record(raw)
        assert sha(raw)==block_terminal['artifact_sha256'][str(raw.relative_to(ROOT))]==original_audit['artifact_sha256'][str(raw.relative_to(ROOT))]
        rows=[json.loads(s) for s in raw.read_text().splitlines()]
        assert len(rows)==1472
        matrix={(r['query'],r['method']):r for r in rows}
        assert len(matrix)==1472 and set(matrix)=={(q,m) for q in queries for m in plan['methods']}
        cases[block['name']]=matrix
        for row in rows:
            validation_time(row)
            if row['method']=='native-excess':continue
            rows_checked+=1;query=queries[row['query']]
            label=f"{block['name']}/{row['query']}/{row['method']}"
            suffix='.its-original.json' if row['method']=='its-mcc' else '.log'
            log=output/f"{row['query']}.{row['method']}.0{suffix}";record(log)
            check(sha(log)==block_terminal['artifact_sha256'][str(log.relative_to(ROOT))],label+': raw log changed')
            expired=(row.get('resources') or {}).get('systemd_result') in ('timeout','oom-kill')
            check(row['outer_timeout']==(expired or row['wall_seconds']>5),label+': outer timeout classification differs')
            if row['method']=='its-mcc':
                expected,read_failure=reconstruct_its(query,row,log,record,lambda c,m:check(c,label+': '+m))
                read_failures+=read_failure
            else:
                expected=admit(parse_formulas(log.read_text(),query,row['exit_code'],expired,row['wall_seconds']),row)
            for field in ['verdict','observed_verdict','formula_output','observed_formula_results','capability_failures','subprocess_error','admission_failures']:
                check(row.get(field)==expected.get(field),label+': reconstructed '+field+' differs')
            truth=None if expected['verdict']=='unknown' else ((expected['verdict']=='reachable')==(query['kind']=='EF'))
            check(row['property_truth'] is truth,label+': reconstructed truth differs')
            admission_counts[row['method']+'/'+expected['verdict']]+=1
            raw_truths=set(expected.get('observed_formula_results',[]))
            if len(raw_truths)==1 and expected['verdict']=='unknown':
                raw_truth=next(iter(raw_truths))=='TRUE'
                raw_verdict='reachable' if raw_truth==(query['kind']=='EF') else 'unreachable'
                demotions.append(dict(block=block['name'],query=row['query'],method=row['method'],
                                      observed_verdict=raw_verdict,observed_property_truth=raw_truth,
                                      reasons=expected['admission_failures']))
    groups=defaultdict(list)
    for name,q in queries.items():groups[tuple(b['sha256'] for b in q['branches'])].append(name)
    representatives={min(names) for names in groups.values()}
    assert len(queries)==368 and len(representatives)==366
    cohorts={'pooled':set(queries)}
    cohorts.update({name:{q for q,v in queries.items() if v['source_corpus']==name} for name in ['existing176','expansion192']})
    cohorts.update({name:{q for q,v in queries.items() if v['family']==name} for name in sorted({q['family'] for q in queries.values()})})
    views={name:{kind:aggregate(selected,plan['methods'],cases)
                 for kind,selected in [('all_properties',members),('representatives',members&representatives)]}
           for name,members in cohorts.items()}
    compare(views,summary['views'],'summary/views')
    rejected_by_method={m:dict(rows=sum(d['method']==m for d in demotions),
        overlapping_reasons=dict(Counter(reason for d in demotions if d['method']==m for reason in d['reasons'])),
        reason_combinations=dict(Counter('; '.join(d['reasons']) for d in demotions if d['method']==m)))
        for m in plan['methods'] if m!='native-excess'}
    result=dict(status='passed' if not issues else 'failed',issues=issues,source_sha256=sha(Path(__file__)),
        plan_sha256=sha(F/'plan.json'),main_audit_sha256=sha(F/'audit-v2.json'),summary_sha256=sha(F/'summary.json'),
        external_rows_checked=rows_checked,reconstructed_outcomes=dict(admission_counts),
        rejected_observed_definitive=demotions,rejected_observed_definitive_by_method=rejected_by_method,recorded_underlying_read_failures=read_failures,
        views=views,artifact_sha256=evidence,
        scope='Independent local reconstruction of frozen external admission rules, including unknown rows, and separate aggregate implementation, after the documented Z3 provenance amendment. Contended pilot. No solver or checker executed. Historical underlying-log read failures use their saved readable-prefix evidence and remain unknown.')
    with (F/'analysis-supplement.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    text=['# Supplemental saved-evidence audit','',f"Status: {result['status']}. Reconstructed {rows_checked} external rows across both complete blocks.",'',
        'Coverage, paired gains/losses, repeated solved sets, PAR-2, summed solver/checker costs and conditional timing ratios were recomputed independently for all slots and representatives, by corpus and family.',
        '',f'{len(demotions)} observed definitive external outputs were rejected by the frozen admission rules; exact reasons remain in the JSON.',
        '',f'Historical underlying-log read failures retained: {read_failures}.','',
        'This supplements the frozen artifact audit under the documented Z3 provenance amendment; the original failed audit remains preserved. The measurement is a contended pilot. It changes no row, deadline, score or reporting rule and executes no solver or proof checker.','']
    text += ['| Method | Rejected definitive formula outputs | Overlapping rejection reasons |',
             '|---|---:|---|']
    for method,counts in rejected_by_method.items():
        reasons=', '.join(f'{key}: {value}' for key,value in sorted(counts['overlapping_reasons'].items())) or 'none'
        text.append(f"| {method} | {counts['rows']} | {reasons} |")
    text += ['', 'These counts describe consistent raw FORMULA results rejected as unknown. They include ITS outputs printed before its wrapper completed. They are separate from accepted coverage; rejection reasons can overlap.','']
    if issues:text+=['Issues:','']+['- '+s for s in issues]
    with (F/'analysis-supplement.md').open('x') as out:out.write('\n'.join(text)+'\n')
    print(json.dumps(dict(status=result['status'],external_rows_checked=rows_checked,issues=len(issues))))
    raise SystemExit(bool(issues))


if __name__=='__main__':main()
