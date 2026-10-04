import unittest
from analyze_original_comparison import analyze

class OriginalComparisonTests(unittest.TestCase):
    def fixture(self):
        return ({'queries':[{'name':'q','suite':'external','family':'model','branches':[{},{}]}]},
                {'property_order':['q'],'methods':['native','external'],'repeat':1,'native_tools':{'native':{}}},
                [{'query':'q','method':'native','repeat':0,'verdict':'reachable','wall_seconds':1,
                  'branches':[{'branch':0,'verdict':'unknown'}, {'branch':1,'verdict':'reachable','independent_check':'python-witness'}]},
                 {'query':'q','method':'external','repeat':0,'verdict':'unknown','wall_seconds':2}])

    def test_suite_and_family_are_distinct(self):
        m,e,r=self.fixture()
        self.assertIn('model',analyze(m,e,r)['families'])
        del m['queries'][0]['family']
        a=analyze(m,e,r,'suite')
        self.assertEqual(a['suites']['external']['solved'],{'native':1,'external':0})
        self.assertNotIn('families',a)

    def test_reject_incomplete_duplicate_and_disagreeing(self):
        m,e,r=self.fixture()
        for rows in (r[:1],r+r[:1]):
            with self.assertRaises(ValueError):analyze(m,e,rows)
        r[1]['verdict']='unreachable'
        with self.assertRaises(ValueError):analyze(m,e,r)

    def test_negative_needs_every_branch_checked(self):
        m,e,r=self.fixture()
        r[0]['verdict']='unreachable'
        r[0]['branches'][1]['verdict']='unreachable'
        r[0]['branches'][1]['independent_check']='python-certificate'
        with self.assertRaises(ValueError):analyze(m,e,r)
        r[0]['branches'][0].update(verdict='unreachable',independent_check='python-certificate')
        self.assertEqual(analyze(m,e,r)['stable_solved']['native'],1)

if __name__=='__main__':unittest.main()
