"""Owned lexical/deferred-context boundaries for source-realizable certificates."""
import ast
from itertools import combinations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'integration')]
from pyflakes_source import export_source,make_source_certificate
from source_pair import SourcePair,make_pair_certificate,check_pair_certificate

class SourceContextTests(unittest.TestCase):
    def test_multiline_splices_in_both_directions_and_every_subset(self):
        forms=['result = x is 1\n','result = (\n    x is\n    2\n)\n',
               'result = (\n    (x) is (\n        3\n    )\n)\n']
        for before in forms:
            for after in forms:
                pair=SourcePair(before,after,'2.1.1','2.2.0')
                for size in range(len(pair.blocks)+1):
                    for selected in combinations(pair.blocks,size):
                        text,release,frame=pair.hybrid(selected)
                        ast.parse(text)
                        self.assertEqual(frame.frame,pair.before.frame)
                anchor=pair.before.model['targets'][0]['anchor']
                packet=make_pair_certificate(before,after,'2.1.1','2.2.0',anchor)
                self.assertTrue(check_pair_certificate(before,after,'2.1.1','2.2.0',packet)[0])

    def test_deferred_typing_contexts_refuse_before_either_certificate_route(self):
        forms=['import typing\nx=0\ntyping.cast("x is 5",x)\nx == 0\n',
               'from typing import cast as c\nx=0\nc("x is 5",x)\nx == 0\n',
               'import typing as t\nx=0\nT=t.List["x is 5"]\nx == 0\n',
               'T = Unknown["x is 5"]\nx == 0\n']
        for text in forms:
            for release in ('2.1.1','2.2.0'):
                with self.subTest(release=release,text=text):
                    with self.assertRaisesRegex(ValueError,'deferred context'):
                        export_source(text,release)
                    with self.assertRaises(ValueError):
                        make_source_certificate(text,release,release,'L4C0P0')
                    with self.assertRaises(ValueError):
                        SourcePair(text,text,release,release)

if __name__=='__main__':unittest.main()
