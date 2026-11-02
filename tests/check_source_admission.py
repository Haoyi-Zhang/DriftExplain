"""Owned admission regressions; parse strings only, never run an analyzer."""
import ast
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'integration')]
from pyflakes_source import export_source, make_source_certificate, check_source_certificate
from source_pair import SourcePair, make_pair_certificate, check_pair_certificate


@unittest.skipUnless(hasattr(ast, 'TypeVar'), 'type-parameter grammar needs Python 3.12+')
class TypeParameterAdmissionTests(unittest.TestCase):
    releases = ('2.1.1', '2.2.0')
    bound = 'class C[T: (x is ())]:\n    pass\n'

    def generic_forms(self):
        for parameters in ('T', '**P', '*Ts', 'T: (x is ())'):
            for header, body in (('class C', 'pass'), ('def f', 'return x is ()'),
                                 ('async def f', 'return x is ()')):
                arguments = '' if header == 'class C' else '(x)'
                yield f'{header}[{parameters}]{arguments}:\n    {body}\n'

    def test_generic_class_bound_does_not_become_a_policy_upgrade(self):
        # The former F/T certificate was for a comparison outside the pinned
        # release's class visitor, not a new native observation.
        self.assertTrue(any(type(n) is ast.Compare for n in ast.walk(ast.parse(self.bound))))
        for release in self.releases:
            with self.subTest(release=release), self.assertRaisesRegex(ValueError, 'newer-syntax'):
                export_source(self.bound, release)

    def test_all_generic_declaration_and_parameter_kinds_are_refused(self):
        for source in self.generic_forms():
            # A parser rejection would not exercise the admission gate.
            tree = ast.parse(source)
            self.assertTrue(tree.body[0].type_params)
            for release in self.releases:
                with self.subTest(source=source, release=release), self.assertRaisesRegex(ValueError, 'newer-syntax'):
                    export_source(source, release)

    def test_source_producer_refuses_before_finite_certificate_generation(self):
        with mock.patch('producer.make_certificate', side_effect=AssertionError('finite producer reached')) as generate:
            with self.assertRaisesRegex(ValueError, 'newer-syntax'):
                make_source_certificate(self.bound, *self.releases, 'L1C12P0')
            generate.assert_not_called()

    def test_source_receiver_refuses_before_finite_acceptance(self):
        source = 'x is ()\n'
        packet = make_source_certificate(source, *self.releases, 'L1C0P0')
        with mock.patch('checker.check_certificate', side_effect=AssertionError('finite receiver reached')) as receive:
            with self.assertRaisesRegex(ValueError, 'newer-syntax'):
                check_source_certificate(self.bound, *self.releases, packet)
            receive.assert_not_called()

    def test_pair_constructor_producer_and_receiver_share_refusal(self):
        for source in self.generic_forms():
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, 'newer-syntax'):
                    SourcePair(source, source, *self.releases)
                with self.assertRaisesRegex(ValueError, 'newer-syntax'):
                    make_pair_certificate(source, source, *self.releases, 'unused')
                with mock.patch('checker.check_certificate', side_effect=AssertionError('finite receiver reached')) as receive:
                    accepted, reason = check_pair_certificate(source, source, *self.releases, {})
                    self.assertFalse(accepted)
                    self.assertIn('newer-syntax', reason)
                    receive.assert_not_called()


class OrdinaryAdmissionTests(unittest.TestCase):
    def test_ordinary_class_sync_and_async_scopes_still_export_and_accept(self):
        source = ('class C:\n    def f(self, x):\n        return x is ()\n'
                  'async def g(x):\n    return x is not 5\n')
        exported = export_source(source, '2.2.0')
        self.assertEqual(len(exported['locations']), 2)
        for location in exported['locations']:
            packet = make_source_certificate(source, '2.1.1', '2.2.0', location['anchor'])
            self.assertTrue(check_source_certificate(source, '2.1.1', '2.2.0', packet)[0])
        pair = SourcePair(source, source, '2.1.1', '2.2.0')
        for target in pair.after.model['targets']:
            packet = make_pair_certificate(source, source, '2.1.1', '2.2.0', target['anchor'])
            self.assertTrue(check_pair_certificate(source, source, '2.1.1', '2.2.0', packet)[0])


if __name__ == '__main__':
    unittest.main()
