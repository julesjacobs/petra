import copy
import unittest
from benchmark import verify_proof

class SparseCheckerTests(unittest.TestCase):
    def test_exact_farkas_proof_and_mutations(self):
        p=dict(places=['a','b'],initial=[1,0],transitions=[dict(pre=[[0,1]],post=[[1,1]])],
               target=[dict(coefficients=[1,1],bound=2,equality=False)])
        proof=dict(kind='sparse-farkas-v1',multipliers=[[2,'1']])
        self.assertEqual(verify_proof(p,proof),'python-sparse-farkas')
        for bad in ([[2,'-1']], [[2,'0']], [[99,'1']], [[2,'1'],[2,'1']]):
            with self.assertRaises(AssertionError):verify_proof(p,dict(proof,multipliers=bad))
        forged=copy.deepcopy(p);forged['transitions'][0]['post']=[[1,2]]
        with self.assertRaises(AssertionError):verify_proof(forged,proof)
        forged=copy.deepcopy(p);forged['initial']=[2,0]
        with self.assertRaises(AssertionError):verify_proof(forged,proof)

    def test_equality_orientation(self):
        p=dict(places=['a'],initial=[2],transitions=[],target=[dict(coefficients=[1],bound=1,equality=True)])
        self.assertEqual(verify_proof(p,dict(kind='sparse-farkas-v1',multipliers=[[1,'1']])), 'python-sparse-farkas')
        with self.assertRaises(AssertionError):verify_proof(p,dict(kind='sparse-farkas-v1',multipliers=[[2,'1']]))

if __name__=='__main__':unittest.main()
