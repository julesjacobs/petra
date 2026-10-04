#!/usr/bin/env python3
"""Reject forged invariant certificates using the independent Python checker."""
import copy
import json
import pathlib
import subprocess
import unittest

from benchmark import verify

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CheckerTests(unittest.TestCase):
    def solve(self, name, method):
        path = ROOT/'benchmarks/smpt-classic'/name/'branch-0.json'
        answer = json.loads(subprocess.check_output([str(ROOT/'target/release/vass-reach'), '--json',str(path),
            '--method',method,'--seconds','1'],text=True))
        self.assertEqual(answer['verdict'],'unreachable')
        return json.loads(path.read_text()),answer

    def test_interval_induction_and_arithmetic(self):
        problem, answer = self.solve('Expressiveness__PGCD','interval-invariant')
        self.assertEqual(verify(problem,answer),'python-interval-invariant')
        for bound in [0,3]:
            forged=copy.deepcopy(answer)
            forged['proof']['regions'][0]['lower'][0]=bound
            with self.assertRaises(AssertionError): verify(problem,forged)
        bad=copy.deepcopy(problem)
        bad['transitions'][0]['pre']=[[0,2]]
        bad['transitions'][0]['post']=[[0,1],[1,1]]
        with self.assertRaises(AssertionError): verify(bad,answer)

    def test_projection_target_and_closure(self):
        problem,answer=self.solve('Performance__NTest__w2','projected-cegar')
        self.assertEqual(verify(problem,answer),'python-projected-closure')
        bad=copy.deepcopy(answer);bad['proof']['places']=[]
        with self.assertRaises(AssertionError): verify(problem,bad)
        bad=copy.deepcopy(answer);bad['proof']['closure']['states']=[]
        with self.assertRaises(AssertionError): verify(problem,bad)


if __name__=='__main__': unittest.main()
