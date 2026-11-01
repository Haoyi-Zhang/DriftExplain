"""Portable source-interface controls; separate from the retained 46 base tests."""
import unittest
import ast
from dataclasses import replace
from itertools import combinations, product
from source_bridge import extract, patch_source, compiler_warnings, _SourceCoordinates
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

    def test_physical_lines_form_feeds_both_directions_and_every_subset(self):
        pairs = [
            ('def f(x):\f\n    return x==x\n',
             'def f(x):\f\n    return x is (100)\n'),
            ('# before\fcomment\ndef f(x):\n    return x is 5\n',
             '# after\fcomment\ndef f(x):\n    return x is 6\n'),
            ('# first\fcomment\ndef f(x):\n    return x==x\n# between\fcomment\ndef g(x):\n    return x is 5\n',
             '# first\fcomment\ndef f(x):\n    return x is 100\n# between\fcomment\ndef g(x):\n    return x == 6\n'),
        ]
        for (left, right), newline in product(pairs, ('\n', '\r\n', '\r')):
            for old, new in ((left, right), (right, left)):
                before, after = (extract(s.replace('\n', newline)) for s in (old, new))
                delta = compute_delta(before.model, after.model)
                for size in range(len(delta) + 1):
                    for selected in combinations(delta, size):
                        with self.subTest(old=old, new=new, newline=repr(newline), size=size):
                            source = patch_source(before, after, [a['id'] for a in selected])
                            hybrid = extract(source)
                            self.assertEqual(hybrid.model, apply_operations(before.model, selected))
                            wanted = {t['anchor'] for t in hybrid.model['targets']
                                      if t['raw']['identity'] == t['raw']['constant'] == 'T'}
                            self.assertEqual({w['anchor'] for w in compiler_warnings(hybrid)}, wanted)

    def test_output_guard_rejects_valid_syntax_spliced_at_wrong_coordinate(self):
        before = extract('def f(x):\n    return x is 5\n')
        after = extract('def f(x):\n    return x is 6\n')
        # Both faulty slots point at the same space, so syntax still parses
        # and the old source survives. Only the commuting-square check catches it.
        key = 'program|f|constant'
        old_start, new_start = before.source.index(' 5'), after.source.index(' 6')
        before = replace(before, slots={**before.slots, key: (old_start, old_start + 1)})
        after = replace(after, slots={**after.slots, key: (new_start, new_start + 1)})
        for old, new in ((before, after), (after, before)):
            with self.assertRaisesRegex(ValueError, 'finite patch disagree'):
                patch_source(old, new, [key])

    def test_utf8_byte_columns_are_not_string_columns(self):
        for newline in ('\n', '\r\n', '\r'):
            source = ('# note\fnot a physical newline\n'
                      '\u00e9 = "\u503c"; result = x is 5\n').replace('\n', newline)
            node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Compare))
            positions = _SourceCoordinates(source)
            start = positions.ast_offset(node.lineno, node.col_offset)
            end = positions.ast_offset(node.end_lineno, node.end_col_offset)
            self.assertEqual(source[start:end], 'x is 5')
            self.assertEqual(start, source.index('x is 5'))
            self.assertNotEqual(start, positions.starts[node.lineno - 1] + node.col_offset)
        with self.assertRaisesRegex(ValueError, 'splits a UTF-8 character'):
            _SourceCoordinates('\u00e9 = 0\n').ast_offset(1, 1)

    def test_utf8_remains_outside_the_public_ascii_contract(self):
        for source in ('# \u503c\ndef f(x):\n    return x is 5\n',
                       'def caf\u00e9(x):\n    return x is 5\n'):
            with self.assertRaisesRegex(ValueError, 'ASCII'):
                extract(source)


if __name__ == '__main__':
    unittest.main()
