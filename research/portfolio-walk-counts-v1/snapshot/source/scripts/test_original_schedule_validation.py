"""Validate scheduler result snapshots without invoking a solver or benchmark."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from native_original import translate
from rust_original_validation import validate
from benchmark_smpt_classic import rust_original
from test_native_original import NET, ATOM, prop

NEGATIVE = '<integer-le><integer-constant>2</integer-constant><tokens-count><place>p</place></tokens-count></integer-le>'


class OriginalScheduleValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'net.pnml').write_text(NET)
        self.log=self.root/'answer.json'

    def inputs(self, predicates, invariant=False):
        predicate='<disjunction>'+''.join(predicates)+'</disjunction>'
        kind='AG' if invariant else 'EF'
        if invariant:predicate='<negation>'+predicate+'</negation>'
        (self.root/'property.xml').write_text('<property-set>'+prop(kind=kind,predicate=predicate)+'</property-set>')
        net,query=translate(self.root/'net.pnml',self.root/'property.xml','requested')
        branches=[]
        for i,target in enumerate(query['targets']):
            path=self.root/f'branch-{i}.json';path.write_text(json.dumps(dict(net,target=target)))
            branches.append(dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        return dict(name='schedule',property_id='requested',kind=kind,branches=branches,
                    pnml='net.pnml',xml='property.xml',pnml_sha256=hashlib.sha256((self.root/'net.pnml').read_bytes()).hexdigest(),
                    xml_sha256=hashlib.sha256((self.root/'property.xml').read_bytes()).hexdigest())

    def positive(self):return dict(verdict='reachable',method='snapshot',trace=[0],marking=[0])
    def negative(self):return dict(verdict='unreachable',method='snapshot',proof=dict(kind='threshold-closure-v1',thresholds=[2],states=[[0],[1]]))
    def unknown(self):return dict(verdict='unknown',method='snapshot')
    def summary(self,query,outcomes,deadline=False):
        verdict='unknown' if deadline else 'reachable' if any(x['verdict']=='reachable' for x in outcomes) else 'unreachable' if len(outcomes)==len(query['branches']) and all(x['verdict']=='unreachable' for x in outcomes) else 'unknown'
        return dict(kind='original-property-v1',property_id=query['property_id'],property_kind=query['kind'],branch_count=len(query['branches']),
                    verdict=verdict,property_truth=None if verdict=='unknown' else (verdict=='reachable')==(query['kind']=='EF'),
                    deadline_exceeded=deadline,parse_seconds=0.0,solve_seconds=0.0,
                    attempts=[dict(branch=i,outcome=x) for i,x in enumerate(outcomes)])
    def check(self,query,answer,outer_timeout=False):
        self.log.write_text(json.dumps(answer))
        return validate(dict(query=query,corpus=str(self.root),log=str(self.log),exit_code=0,response_bytes=1024**2,outer_timeout=outer_timeout))

    def test_final_retry_snapshot_keeps_cached_refutation_and_winner(self):
        for invariant in (False,True):
            query=self.inputs([NEGATIVE,ATOM,ATOM],invariant)
            result=self.check(query,self.summary(query,[self.negative(),self.positive()]))
            self.assertEqual(result['verdict'],'reachable')
            self.assertIs(result['property_truth'],not invariant)
            self.assertEqual([b['branch'] for b in result['branches']],[0,1])
            self.assertEqual(result['independent_checks'],['python-threshold-closure','python-witness'])

    def test_unresolved_earlier_branch_does_not_hide_later_witness(self):
        query=self.inputs([ATOM,ATOM])
        result=self.check(query,self.summary(query,[self.unknown(),self.positive()]))
        self.assertEqual(result['verdict'],'reachable')
        self.assertEqual(result['branches'][0]['verdict'],'unknown')
        self.assertEqual(result['branches'][1]['independent_check'],'python-witness')

    def test_final_negative_needs_every_independently_refuted_branch(self):
        query=self.inputs([NEGATIVE,NEGATIVE,NEGATIVE])
        answer=self.summary(query,[self.negative() for _ in range(3)])
        self.assertEqual(self.check(query,answer)['verdict'],'unreachable')
        for index in range(3):
            unchecked=copy.deepcopy(answer)
            unchecked['attempts'][index]['outcome']=dict(verdict='unreachable',method='unchecked')
            result=self.check(query,unchecked)
            self.assertEqual(result['verdict'],'unknown')
            self.assertIsNone(result['property_truth'])
        partial=self.summary(query,[self.negative()])
        self.assertEqual(self.check(query,partial)['verdict'],'unknown')

    def test_retry_history_duplicate_ids_gaps_and_tail_after_winner_are_rejected(self):
        query=self.inputs([ATOM,ATOM,ATOM])
        good=self.summary(query,[self.unknown(),self.positive()])
        malformed=[]
        duplicate=copy.deepcopy(good);duplicate['attempts'].insert(1,dict(branch=0,outcome=self.unknown()));malformed.append(duplicate)
        gap=copy.deepcopy(good);gap['attempts'][1]['branch']=2;malformed.append(gap)
        tail=copy.deepcopy(good);tail['attempts'].append(dict(branch=2,outcome=self.unknown()));malformed.append(tail)
        for answer in malformed:
            with self.assertRaises(ValueError):self.check(query,answer)

    def test_deadline_censors_cached_positive_and_all_negative_snapshots(self):
        for predicates,outcomes in [([ATOM,ATOM],[self.positive()]),([NEGATIVE,NEGATIVE],[self.negative(),self.negative()])]:
            query=self.inputs(predicates)
            answer=self.summary(query,outcomes,deadline=True)
            result=self.check(query,answer)
            self.assertEqual(result['verdict'],'unknown');self.assertIsNone(result['property_truth'])
            answer['verdict']='reachable' if outcomes[0]['verdict']=='reachable' else 'unreachable'
            with self.assertRaisesRegex(ValueError,'aggregate verdict'):self.check(query,answer)
            self.assertEqual(self.check(query,{},outer_timeout=True)['verdict'],'unknown')

    def test_unattempted_tail_and_original_source_are_still_checked(self):
        query=self.inputs([ATOM,NEGATIVE])
        answer=self.summary(query,[self.positive()])
        tail=self.root/query['branches'][1]['path']
        problem=json.loads(tail.read_text());problem['initial']=[9];tail.write_text(json.dumps(problem))
        query['branches'][1]['sha256']=hashlib.sha256(tail.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'canonical branch 1'):self.check(query,answer)
        query=self.inputs([ATOM,NEGATIVE]);answer=self.summary(query,[self.positive()])
        (self.root/'net.pnml').write_text(NET+'\n')
        with self.assertRaisesRegex(ValueError,'checksum'):self.check(query,answer)

    def test_outer_adapter_censors_late_success_with_geometric_flag(self):
        query=self.inputs([ATOM,ATOM])
        args=SimpleNamespace(binary=self.root/'unused',baseline_binary=self.root/'unused',seconds=3,max_states=100,
                             outer_grace=0,geometric_branches_method=['candidate'])
        for wall,expired in [(3.01,False),(1.0,True)]:
            with patch('benchmark_smpt_classic.execute',return_value=(wall,0,expired,{})) as execute,patch('bounded_validation.run_validation') as checker:
                result=rust_original(query,self.root,self.root,'candidate',0,args)
            self.assertIn('--geometric-branches',execute.call_args.args[0])
            self.assertEqual(result['verdict'],'unknown')
            self.assertTrue(result['outer_timeout'])
            checker.assert_not_called()


if __name__=='__main__':unittest.main()
