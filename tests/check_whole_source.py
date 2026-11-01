from pathlib import Path
import sys
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'integration'),str(Path(__file__).resolve().parents[1]/'src')]
from pyflakes_source import export_source, make_source_certificate, check_source_certificate
from producer import evaluate_family

class WholeSourceTests(unittest.TestCase):
    def values(self, source, version):
        e=export_source(source,version)
        return [evaluate_family(e['model'],'IsLiteral',r['anchor'])['value'] for r in e['locations']]
    def test_nested_scope_and_both_sides(self):
        s="def f(x):\n    if 'left' is not x:\n        return x is (1, (None,))\n"
        self.assertEqual(self.values(s,'2.1.1'),['T','F'])
        self.assertEqual(self.values(s,'2.2.0'),['T','T'])
    def test_chain_singletons_and_nonconstant_tuple(self):
        self.assertEqual(self.values('x is True < 4 is not x\n','2.2.0'),['F','F','T'])
        self.assertEqual(self.values('x is (x,)\n','2.2.0'),['F'])
    def test_comments_and_strings_do_not_supply_comparisons(self):
        self.assertEqual(self.values("# x is 1\ns='x is 2'\n",'2.2.0'),[])
    def test_unsupported_annotation_refuses_instead_of_guessing(self):
        for s in ('a: "x is 1"\n','from __future__ import annotations\nx is 1\n'):
            with self.assertRaises(ValueError): export_source(s,'2.2.0')
    def test_pair_and_source_identities(self):
        a=export_source('x is 1 is y\n','2.2.0')
        self.assertEqual(len({r['anchor'] for r in a['locations']}),2)
        self.assertNotEqual(a['source_sha256'],export_source('x is 2 is y\n','2.2.0')['source_sha256'])
        self.assertNotEqual(a['model']['targets'][0]['origins'],export_source('x is 2 is y\n','2.2.0')['model']['targets'][0]['origins'])
    def test_receiver_rebuild_and_source_release_binding(self):
        s='x is ()\n';a=export_source(s,'2.2.0')['locations'][0]['anchor']
        p=make_source_certificate(s,'2.1.1','2.2.0',a)
        self.assertTrue(check_source_certificate(s,'2.1.1','2.2.0',p)[0])
        self.assertFalse(check_source_certificate(s+'# changed bytes\n','2.1.1','2.2.0',p)[0])
        self.assertFalse(check_source_certificate(s,'2.2.0','2.1.1',p)[0])
        p['certificate']['witness']=[]
        self.assertFalse(check_source_certificate(s,'2.1.1','2.2.0',p)[0])
if __name__=='__main__':unittest.main()
