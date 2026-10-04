import unittest
from benchmark import verify_proof

class SparseFarkasTests(unittest.TestCase):
    def fixture(self):
        return (dict(places=['a','b'],initial=[1,0],transitions=[
            dict(name='move',pre=[[0,1]],post=[[1,1]]),
            dict(name='reset',pre=[[1,1]],post=[[0,1]])],
            target=[dict(coefficients=[0,1],bound=2,equality=False)]),
            dict(kind='sparse-farkas-v1',multipliers=[[0,'1'],[2,'1']]))

    def test_valid_capacity_proof(self):
        p,c=self.fixture()
        self.assertEqual(verify_proof(p,c),'python-sparse-farkas')

    def test_reachable_target_rejected(self):
        p,c=self.fixture();p['target'][0]['bound']=1
        with self.assertRaises(ValueError):verify_proof(p,c)

    def test_increasing_potential_rejected(self):
        p,c=self.fixture();p['transitions'][0]['post'][0][1]=2
        with self.assertRaises(ValueError):verify_proof(p,c)

    def test_malformed_multipliers_rejected(self):
        p,c=self.fixture()
        for terms in ([[0,'-1'],[2,'1']], [[0,'0'],[2,'1']], [[0,True],[2,'1']],
                      [[True,'1'],[2,'1']], [[0,'1'],[0,'1'],[2,'1']],
                      [[2,'1'],[0,'1']], [[3,'1']], []):
            c['multipliers']=terms
            with self.subTest(terms=terms),self.assertRaises(ValueError):verify_proof(p,c)

    def test_exact_arithmetic_and_equality_row_sign(self):
        p,c=self.fixture();p['target'][0]['equality']=True
        c['multipliers']=[[0,'100000000000000000001/7'],[3,'100000000000000000001/7']]
        self.assertEqual(verify_proof(p,c),'python-sparse-farkas')
        c['multipliers'][1][0]=2
        with self.assertRaises(ValueError):verify_proof(p,c)

if __name__=='__main__':unittest.main()
