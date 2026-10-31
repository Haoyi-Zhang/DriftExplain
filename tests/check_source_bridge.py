"""Portable source-interface controls; separate from the retained 46 base tests."""
import unittest
from itertools import combinations, product
from source_bridge import extract, patch_source, compiler_warnings
from producer import compute_delta, apply_operations, make_certificate
from checker import check_certificate


class SourceBridgeTests(unittest.TestCase):
    def test_native_warning_and_canonical_evidence_agree(self):
        item = extract('def focus(x):\n    return x is 5\n')
        self.assertEqual([entry['anchor'] for entry in compiler_warnings(item)], ['focus'])
        self.assertEqual(item.model['targets'][0]['raw'], {'identity': 'T', 'constant': 'T'})

    def test_unsupported_syntax_is_not_silently_omitted(self):
        for source in ('import os\n', 'def f(x):\n    return x < 5\n',
                       'def f(x):\n    return x is None\n',
                       'def f(x):\n    return x\n',
                       'def f(x):\n    print(x)\n    return x is 5\n',
                       'def f(x):\n    return x == x\ndef f(x):\n    return x is 5\n'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                extract(source)

    def test_variable_length_disjoint_source_splices_commute(self):
        before = extract('def f(x):\n    return x == x\n')
        after = extract('def f(x):\n    return x is 100\n')
        operations = compute_delta(before.model, after.model)
        for selected in ([], operations[:1], operations[1:], operations):
            hybrid = extract(patch_source(before, after, [item['id'] for item in selected]))
            self.assertEqual(hybrid.model, apply_operations(before.model, selected))

    def test_identity_changes_and_unknown_slots_are_rejected(self):
        before = extract('def f(x):\n    return x == x\n')
        after = extract('def g(x):\n    return x is 5\n')
        with self.assertRaises(ValueError):
            patch_source(before, after, [])
        with self.assertRaises(ValueError):
            patch_source(before, before, ['missing'])

    def test_preserved_warning_can_have_nonempty_exact_support(self):
        before = extract('def f(x):\n    return x is 5\n')
        after = extract('def f(x):\n    return x is 6\n')
        certificate = make_certificate(before.model, after.model, 'identity-literal', 'f')
        self.assertEqual(certificate['classification'], 'preserved')
        self.assertEqual(certificate['witness'], ['program|f|constant'])
        self.assertTrue(check_certificate(before.model, after.model, certificate)[0])
        certificate['witness'] = []
        self.assertFalse(check_certificate(before.model, after.model, certificate)[0])

    def test_parentheses_and_compact_operator_splices_commute_for_every_subset(self):
        # These spellings have the same admitted AST grammar; parentheses are
        # not observation fields and cannot leak into an operator footprint.
        expressions = ('x==x', 'x == (x)', '(x)==((x))',
                       'x is 5', 'x is (5)', '(x)is((100))')
        for old, new in product(expressions, repeat=2):
            before = extract('def f(x):\n    return '+old+'\n')
            after = extract('def f(x):\n    return '+new+'\n')
            delta = compute_delta(before.model, after.model)
            for size in range(len(delta)+1):
                for selected in combinations(delta, size):
                    with self.subTest(old=old, new=new, atoms=[a['id'] for a in selected]):
                        hybrid = extract(patch_source(before, after, [a['id'] for a in selected]))
                        self.assertEqual(hybrid.model, apply_operations(before.model, selected))
                        predicted = (hybrid.model['targets'][0]['raw'] == {'identity': 'T', 'constant': 'T'})
                        self.assertEqual(bool(compiler_warnings(hybrid)), predicted)


if __name__ == '__main__':
    unittest.main()
