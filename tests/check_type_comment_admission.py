"""Owned lexical admission checks; no upstream analyzer or source execution."""
import ast
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'integration')]
from pyflakes_source import export_source, make_source_certificate, check_source_certificate
from source_pair import SourcePair, make_pair_certificate, check_pair_certificate


class TypeCommentAdmissionTests(unittest.TestCase):
    releases = ('2.1.1', '2.2.0')
    counterexample = 'a = 0  # type: x is ()\ny is 5\n'
    refused = (
        counterexample,
        'a = 0  #type:x is ()\ny is 5\n',
        'a = 0  #\ttype: x is ()\ny is 5\n',
        '# type: x is ()\ny is 5\n',
        'def f(x):\n    # type: (x is ()) -> int\n    return x is 5\n',
        'a = 0  # type: ignore\ny is 5\n',
        'a = 0  # type: ignore[attr-defined]\ny is 5\n',
        'a = 0  # type: x is ()\r\ny is 5\r\n',
    )
    admitted = (
        '# x is ()\ny is 5\n',
        'a = 0  # ordinary comment mentions type: x is ()\ny is 5\n',
        'a = 0  # note: # type: x is ()\ny is 5\n',
        's = "# type: x is ()"\ny is 5\n',
        's = """first line\n# type: x is ()\nlast line"""\ny is 5\n',
        's = "# type: x is ()"  # ordinary trailing comment\ny is 5\n',
        's = "# type: x is ()"; y is 5\n',
    )

    def test_actual_counterexample_has_no_comment_comparison_in_module_ast(self):
        comparisons = [n for n in ast.walk(ast.parse(self.counterexample))
                       if type(n) is ast.Compare]
        self.assertEqual([n.lineno for n in comparisons], [2])
        for release in self.releases:
            with self.subTest(release=release), self.assertRaisesRegex(ValueError, 'type-comment'):
                export_source(self.counterexample, release)

    def test_type_comment_variants_are_rejected_for_both_policies(self):
        for source in self.refused:
            ast.parse(source)  # The lexical gate, not invalid syntax, rejects.
            for release in self.releases:
                with self.subTest(source=source, release=release):
                    with self.assertRaisesRegex(ValueError, 'type-comment'):
                        export_source(source, release)

    def test_rejection_precedes_finite_production_and_reception(self):
        for source in self.refused:
            for releases in (self.releases, self.releases[::-1]):
                with self.subTest(source=source, releases=releases):
                    with mock.patch('producer.make_certificate',
                                    side_effect=AssertionError('finite producer reached')) as produce:
                        with self.assertRaisesRegex(ValueError, 'type-comment'):
                            make_source_certificate(source, *releases, 'unused')
                        produce.assert_not_called()
                    with mock.patch('checker.check_certificate',
                                    side_effect=AssertionError('finite receiver reached')) as receive:
                        with self.assertRaisesRegex(ValueError, 'type-comment'):
                            check_source_certificate(source, *releases, {})
                        receive.assert_not_called()

    def test_pair_routes_reject_either_endpoint_before_finite_delta_or_checks(self):
        ordinary = 'y is 5\n'
        for source in self.refused:
            for before, after in ((source, ordinary), (ordinary, source)):
                with self.subTest(before=before, after=after):
                    with mock.patch('producer.compute_delta',
                                    side_effect=AssertionError('finite delta reached')) as delta:
                        for route in (SourcePair, make_pair_certificate):
                            args = (before, after, *self.releases)
                            if route is make_pair_certificate:
                                args += ('unused',)
                            with self.assertRaisesRegex(ValueError, 'type-comment'):
                                route(*args)
                        delta.assert_not_called()
                    with mock.patch('checker.check_certificate',
                                    side_effect=AssertionError('finite receiver reached')) as receive:
                        accepted, reason = check_pair_certificate(
                            before, after, *self.releases, {})
                        self.assertFalse(accepted)
                        self.assertIn('type-comment', reason)
                        receive.assert_not_called()

    def test_ordinary_comments_and_string_contents_are_not_type_comments(self):
        for source in self.admitted:
            for release in self.releases:
                with self.subTest(source=source, release=release):
                    exported = export_source(source, release)
                    self.assertEqual(len(exported['locations']), 1)
                    self.assertEqual(exported['model']['targets'][0]['raw'],
                                     {'identity': 'T', 'scalar': 'T', 'tuple': 'F'})

    def test_admitted_text_round_trips_through_both_finite_routes(self):
        for source in self.admitted:
            with self.subTest(source=source):
                anchor = export_source(source, '2.2.0')['locations'][0]['anchor']
                packet = make_source_certificate(source, *self.releases, anchor)
                self.assertTrue(check_source_certificate(source, *self.releases, packet)[0])
                pair = SourcePair(source, source, *self.releases)
                key = pair.after.model['targets'][0]['anchor']
                packet = make_pair_certificate(source, source, *self.releases, key)
                self.assertTrue(check_pair_certificate(source, source, *self.releases, packet)[0])

    def test_unterminated_multiline_text_fails_closed_during_tokenization(self):
        with self.assertRaisesRegex(ValueError, 'tokenization failed'):
            export_source('s = """unterminated\n', '2.2.0')


if __name__ == '__main__':
    unittest.main()
