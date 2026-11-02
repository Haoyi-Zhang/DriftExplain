"""Pure paragraph-binding checks; do not strengthen source-reading claims."""
import csv
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_static import citation_contexts


class CitationContextTests(unittest.TestCase):
    def test_rewrapping_keeps_complete_clause_and_section(self):
        flat = '\\section{Prior}\n\\subsection{Rules}\nA reviewed rule~\\cite{a,b} supplies evidence.\n'
        wrapped = '\\section{Prior}\n\\subsection{Rules}\nA reviewed\nrule~\\cite{a,b}\nsupplies evidence.\n'
        expected = {'a': {('Prior / Rules', 'A reviewed rule~[citation] supplies evidence.')},
                    'b': {('Prior / Rules', 'A reviewed rule~[citation] supplies evidence.')}}
        self.assertEqual(citation_contexts(flat), expected)
        self.assertEqual(citation_contexts(wrapped), expected)

    def test_changed_clause_citation_or_section_is_not_same_binding(self):
        source = '\\section{Prior}\n\nA reviewed rule~\\cite{a} supplies evidence.\n'
        before = citation_contexts(source)
        for changed in (source.replace('reviewed', 'unverified'),
                        source.replace('cite{a}', 'cite{b}'),
                        source.replace('{Prior}', '{Different}')):
            with self.subTest(changed=changed):
                self.assertNotEqual(citation_contexts(changed), before)

    def test_blank_paragraphs_do_not_merge_and_new_section_resets_subsection(self):
        source = ('\\section{First}\n\\subsection{Detail}\n\nOne~\\cite{a}.\n\nTwo~\\cite{a}.\n\n'
                  '\\section{Second}\n\\label{sec:second}\nThree~\\cite{b}.\n')
        self.assertEqual(citation_contexts(source), {
            'a': {('First / Detail', 'One~[citation].'), ('First / Detail', 'Two~[citation].')},
            'b': {('Second', 'Three~[citation].')}})

    @unittest.skipUnless((ROOT.parent / 'paper/main.tex').is_file(), 'standalone artifact has no manuscript')
    def test_all_67_current_map_rows_match_real_manuscript_paragraphs(self):
        contexts = citation_contexts((ROOT.parent / 'paper/main.tex').read_text(encoding='utf-8-sig'))
        with (ROOT / 'citation_claim_map.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 67)
        self.assertEqual({r['citation_key'] for r in rows}, set(contexts))
        for row in rows:
            with self.subTest(key=row['citation_key']):
                self.assertIn((row['section'], row['manuscript_claim']), contexts[row['citation_key']])
                self.assertTrue(row['identity_verification'])
                self.assertTrue(row['claim_audit'])
                self.assertTrue(row['audit_limit'])


if __name__ == '__main__':
    unittest.main()
