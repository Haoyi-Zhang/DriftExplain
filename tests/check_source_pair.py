import copy
from itertools import combinations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'integration')]
from source_pair import SourcePair,make_pair_certificate,check_pair_certificate
import producer

class SourcePairTests(unittest.TestCase):
    old='def f(x):\n    return x is 5\n\ndef g(x):\n    return x is ()\n'
    new='# displaced lines\n\ndef f(x):\n    return x is 6\n\ndef g(x):\n    return x == ()\n'
    def test_whitespace_displacement_uses_stable_paths_not_line_number(self):
        pair=SourcePair(self.old,self.new,'2.1.1','2.2.0')
        self.assertNotEqual(next(iter(pair.before.locations.values()))['line'],next(iter(pair.after.locations.values()))['line'])
        self.assertEqual(pair.before.slots.keys(),pair.after.slots.keys())
    def test_every_block_subset_is_real_source_and_exact_minimal_support(self):
        pair=SourcePair(self.old,self.new,'2.1.1','2.2.0');keys=list(pair.blocks)
        for target in pair.after.model['targets']:
            anchor=target['anchor'];support,_=pair.support(anchor)
            final=producer.evaluate_family(pair.after.model,'IsLiteral',anchor)
            for n in range(len(keys)+1):
                for subset in combinations(keys,n):
                    _,_,hybrid=pair.hybrid(subset)
                    actual=producer.evaluate_family(hybrid.model,'IsLiteral',anchor)==final
                    self.assertEqual(actual,set(support)<=set(subset))
    def test_internal_observations_are_not_separate_source_edits(self):
        pair=SourcePair('x is ()\n','x is 5\n','2.1.1','2.2.0')
        source_key=next(k for k in pair.blocks if k.startswith('source:'))
        self.assertGreater(len(pair.blocks[source_key]),1)
        with self.assertRaises(ValueError):pair.hybrid([pair.blocks[source_key][0]])
    def test_chains_nesting_other_statement_changes_and_renames_reject(self):
        for a,b in [('x is 1 is y\n','x is 2 is y\n'),('x is (y is 1)\n','x is (y is 2)\n'),
                    ('x=1\nx is 5\n','x=2\nx is 6\n'),(self.old,self.new.replace('def f','def other'))]:
            with self.assertRaises(ValueError):SourcePair(a,b,'2.1.1','2.2.0')
    def test_receiver_reconstructs_binding_and_rejects_stale_support(self):
        pair=SourcePair(self.old,self.new,'2.1.1','2.2.0');anchor=pair.after.model['targets'][0]['anchor']
        p=make_pair_certificate(self.old,self.new,'2.1.1','2.2.0',anchor)
        self.assertTrue(check_pair_certificate(self.old,self.new,'2.1.1','2.2.0',p)[0])
        self.assertFalse(check_pair_certificate(self.old,self.new+'# bytes\n','2.1.1','2.2.0',p)[0])
        q=copy.deepcopy(p);q['source_support']=[]
        self.assertFalse(check_pair_certificate(self.old,self.new,'2.1.1','2.2.0',q)[0])
    def test_operand_rename_inside_whole_comparison_hole_is_admitted(self):
        old='def f(x, y):\n    return x is 1\n'
        new='def f(x, y):\n    return y is 1\n'
        pair=SourcePair(old,new,'2.1.1','2.2.0')
        anchor=pair.after.model['targets'][0]['anchor']
        certificate=make_pair_certificate(old,new,'2.1.1','2.2.0',anchor)
        self.assertTrue(check_pair_certificate(old,new,'2.1.1','2.2.0',certificate)[0])
        with self.assertRaises(ValueError):
            SourcePair(old,new.replace('def f','def g'),'2.1.1','2.2.0')
    def test_no_program_execution(self):
        pair=SourcePair('raise RuntimeError\nx is 5\n','raise RuntimeError\nx is 6\n','2.2.0','2.2.0')
        pair.hybrid(pair.blocks)
if __name__=='__main__':unittest.main()
