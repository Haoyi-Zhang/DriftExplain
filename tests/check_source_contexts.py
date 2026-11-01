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
import producer

class SourceContextTests(unittest.TestCase):
    def test_whole_comparisons_form_feed_comments_both_directions_all_subsets(self):
        # A trailing comment is admitted today without changing the whole-block
        # receiver's ASCII profile or its unmodified source-coordinate code.
        left = 'a = x is 5\nb = x == () # trailing\fcomment\n'
        right = 'a = x == 6\nb = x is (1,) # trailing\fcomment\n'
        for before, after, old_release, new_release in (
                (left, right, '2.1.1', '2.2.0'), (right, left, '2.2.0', '2.1.1')):
            pair = SourcePair(before, after, old_release, new_release)
            keys = list(pair.blocks)
            supports = {t['anchor']: pair.support(t['anchor'])[0] for t in pair.after.model['targets']}
            for size in range(len(keys) + 1):
                for selected in combinations(keys, size):
                    source, release, frame = pair.hybrid(selected)
                    ids = {v for key in selected for v in pair.blocks[key]}
                    expected = producer.apply_operations(pair.before.model,
                        [op for op in pair.delta if op['id'] in ids])
                    self.assertEqual(frame.model, expected)
                    self.assertEqual(frame.frame, pair.before.frame)
                    self.assertEqual(release, new_release if 'policy:literal' in selected else old_release)
                    for anchor, support in supports.items():
                        exact = (producer.evaluate_family(frame.model, 'IsLiteral', anchor) ==
                                 producer.evaluate_family(pair.after.model, 'IsLiteral', anchor))
                        self.assertEqual(exact, set(support) <= set(selected))
            for target in pair.after.model['targets']:
                packet = make_pair_certificate(before, after, old_release, new_release, target['anchor'])
                self.assertTrue(check_pair_certificate(before, after, old_release, new_release, packet)[0])

    def test_whole_comparison_unsafe_form_feed_offsets_remain_fail_closed(self):
        # source_pair.py is outside this repair's write allowlist. Its existing
        # all-subset admission must refuse, not accept an incorrect realization.
        plain = 'result = x is 5\n'
        displaced = '# comment\fnot a newline\nresult = x is 6\n'
        for before, after in ((plain, displaced), (displaced, plain)):
            with self.assertRaises((SyntaxError, ValueError)):
                SourcePair(before, after, '2.1.1', '2.2.0')

    def test_whole_comparison_utf8_profile_refuses_in_both_directions(self):
        plain = 'result = x is 5\n'
        unicode_source = '\u00e9 = "\u503c"; result = x is 6\n'
        # The automatic nonsplicing exporter uses AST byte columns. The source
        # splicer remains explicitly ASCII, so no byte/character guess is made.
        exported = export_source(unicode_source, '2.2.0')
        node = next(n for n in ast.walk(ast.parse(unicode_source)) if type(n) is ast.Compare)
        self.assertEqual(exported['locations'][0]['column'], node.col_offset)
        self.assertGreater(node.col_offset, unicode_source.index('x is 6'))
        for before, after in ((plain, unicode_source), (unicode_source, plain)):
            with self.assertRaisesRegex(ValueError, 'ASCII'):
                SourcePair(before, after, '2.1.1', '2.2.0')

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
