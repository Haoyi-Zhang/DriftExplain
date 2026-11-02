"""Bounded data-only consumer regressions, portable to an artifact-only checkout.

Use the real retained inputs and real verifier/exporter, not fabricated PASS
summaries. Mutations override reads in memory; outputs live only in temporary
directories. No upstream analyzer, compiler, study campaign or network is run.
"""
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'integration'))
import check_source_pairs as verifier
import report_source_pairs as exporter

CAPTURE = ROOT / 'results/source-pairs'
CASES = ROOT / 'results/source_consumer/cases.json'
SUMMARY = CAPTURE / 'summary.json'
REGISTRATION = CAPTURE / 'registration.json'
RECORDS = CAPTURE / 'records.json'
INPUTS = CAPTURE / 'native-inputs.json'
EXPECTED_COUNTS = {
    'source_inputs': 31, 'admitted_pairs': 27, 'excluded_pairs': 4,
    'source_realizable_hybrids': 108, 'native_parse_observations': 216,
    'source_certificate_targets': 27, 'exact_support_subset_checks': 108,
    'native_model_disagreements': 0, 'natural_maintenance_commits': 0,
}
EXPECTED_TEX = (
    '\\newcommand{\\SourcePairInputs}{31}\n'
    '\\newcommand{\\SourcePairAdmitted}{27}\n'
    '\\newcommand{\\SourcePairExcluded}{4}\n'
    '\\newcommand{\\SourcePairHybrids}{108}\n'
    '\\newcommand{\\SourcePairNative}{216}\n'
)


@contextmanager
def capture(*, values=None, missing=(), texts=None):
    overrides = {p.resolve(): json.dumps(v) for p, v in (values or {}).items()}
    overrides.update({p.resolve(): v for p, v in (texts or {}).items()})
    absent = {p.resolve() for p in missing}
    read_text, is_file = Path.read_text, Path.is_file

    def read(path, *args, **kwargs):
        if path.resolve() in absent:
            raise FileNotFoundError(path)
        if path.resolve() in overrides:
            return overrides[path.resolve()]
        return read_text(path, *args, **kwargs)

    def exists(path):
        return path.resolve() not in absent and is_file(path)

    with mock.patch.object(Path, 'read_text', read), mock.patch.object(Path, 'is_file', exists):
        yield


class SourcePairConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {p: json.loads(p.read_text(encoding='utf-8'))
                    for p in (CASES, SUMMARY, REGISTRATION, RECORDS, INPUTS)}
        cls.raw = {v: json.loads((CAPTURE / ('raw-' + v + '.json')).read_text(encoding='utf-8'))
                   for v in verifier.RELEASES}

    def rejected(self, *, values=None, missing=(), texts=None, export=False):
        """Exercise actual acceptance; optionally both fresh/occupied exports."""
        with capture(values=values, missing=missing, texts=texts), redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(ValueError):
                verifier.run()
        self.assertEqual(stdout.getvalue(), '')
        if export:
            with tempfile.TemporaryDirectory() as directory:
                existing = Path(directory) / 'existing.tex'
                sentinel = b'owned-existing-output\n'
                existing.write_bytes(sentinel)
                fresh = Path(directory) / 'fresh.tex'
                with capture(values=values, missing=missing, texts=texts):
                    for path in (fresh, existing):
                        with self.subTest(output=path.name), self.assertRaises(ValueError):
                            exporter.render(path)
                self.assertFalse(fresh.exists())
                self.assertEqual(existing.read_bytes(), sentinel)

    def raw_values(self, version, observations):
        raw = deepcopy(self.raw[version])
        raw['stdout'] = json.dumps(observations)
        return {CAPTURE / ('raw-' + version + '.json'): raw}

    def test_genuine_retained_counts_and_exact_macro_output(self):
        with redirect_stdout(io.StringIO()):
            result = verifier.run()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual({k: result[k] for k in EXPECTED_COUNTS}, EXPECTED_COUNTS)
        self.assertEqual(result['measured_sources_differ_from_current'],
                         ['integration/pyflakes_source.py', 'integration/source_pair.py'])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'counts.tex'
            exporter.render(output)
            self.assertEqual(output.read_bytes(), EXPECTED_TEX.encode('utf-8'))

    def test_valid_evidence_still_cannot_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'counts.tex'
            output.write_bytes(b'existing\r\n')
            with self.assertRaises(FileExistsError):
                exporter.render(output)
            self.assertEqual(output.read_bytes(), b'existing\r\n')

    def test_original_two_count_reproductions_refuse_both_consumers(self):
        for key, value in (('source_inputs', 32), ('excluded_pairs', 5)):
            summary = deepcopy(self.data[SUMMARY]); summary[key] = value
            with self.subTest(field=key):
                self.rejected(values={SUMMARY: summary}, export=True)

    def test_all_other_summary_counts_are_reconstructed(self):
        for key, value in EXPECTED_COUNTS.items():
            summary = deepcopy(self.data[SUMMARY]); summary[key] = value + 1
            with self.subTest(field=key):
                self.rejected(values={SUMMARY: summary})

    def test_summary_types_fields_status_and_scope_are_fail_closed(self):
        for key, value in EXPECTED_COUNTS.items():
            for bad in (None, True, False, float(value), str(value), -1):
                summary = deepcopy(self.data[SUMMARY]); summary[key] = bad
                with self.subTest(field=key, value=bad):
                    self.rejected(values={SUMMARY: summary})
            summary = deepcopy(self.data[SUMMARY]); del summary[key]
            with self.subTest(missing=key):
                self.rejected(values={SUMMARY: summary})
        for key, value in (('status', 'FAILED_OR_PARTIAL'),
                           ('application_decisions_or_time_savings_measured', True),
                           ('application_decisions_or_time_savings_measured', 0),
                           ('elapsed_seconds', 1.23)):
            summary = deepcopy(self.data[SUMMARY]); summary[key] = value
            with self.subTest(field=key, value=value):
                self.rejected(values={SUMMARY: summary}, export=True)

    def test_registration_counts_and_upstream_identity_are_checked(self):
        for key in ('source_inputs', 'admitted'):
            for bad in (self.data[REGISTRATION][key] + 1, True, None):
                registration = deepcopy(self.data[REGISTRATION]); registration[key] = bad
                with self.subTest(field=key, value=bad):
                    self.rejected(values={REGISTRATION: registration})
        registration = deepcopy(self.data[REGISTRATION]); registration['test_source_sha256'] = '0' * 64
        self.rejected(values={REGISTRATION: registration})

    def test_null_process_exit_reproduction_refuses_both_consumers(self):
        for version in verifier.RELEASES:
            raw = deepcopy(self.raw[version]); raw['returncode'] = None
            with self.subTest(release=version):
                self.rejected(values={CAPTURE / ('raw-' + version + '.json'): raw}, export=True)

    def test_process_exit_and_output_types_are_strict(self):
        path = CAPTURE / 'raw-2.1.1.json'
        for code in (False, True, [], {}, '', '0', 0.0, 1, -1):
            raw = deepcopy(self.raw['2.1.1']); raw['returncode'] = code
            with self.subTest(returncode=code):
                self.rejected(values={path: raw})
        for key, bad in (('stdout', None), ('stdout', ''), ('stdout', '[]'),
                         ('stderr', None), ('stderr', 'Traceback'), ('extra', 0)):
            raw = deepcopy(self.raw['2.1.1']); raw[key] = bad
            with self.subTest(field=key, value=bad):
                self.rejected(values={path: raw})
        for key in ('returncode', 'stdout', 'stderr'):
            raw = deepcopy(self.raw['2.1.1']); del raw[key]
            with self.subTest(missing=key):
                self.rejected(values={path: raw})

    def test_required_inventory_detects_every_missing_and_empty_file(self):
        for relative in verifier.REQUIRED_EVIDENCE:
            path = ROOT / relative
            with self.subTest(missing=relative):
                self.rejected(missing=(path,))
            with self.subTest(empty=relative):
                self.rejected(texts={path: ''})
        self.rejected(missing=(CAPTURE / 'raw-2.2.0.json',), export=True)
        self.rejected(values={CASES: []}, export=True)
        self.rejected(values={RECORDS: []})
        self.rejected(values={INPUTS: []})

    def test_original_population_and_case_bytes_cannot_be_redefined(self):
        original = self.data[CASES]
        variants = [original[:-1], original + [original[0]], original[:-1] + [original[0]]]
        renamed = deepcopy(original); renamed[0]['id'] = 'unregistered:0'; variants.append(renamed)
        changed = deepcopy(original); changed[0]['source'] += '# changed\n'
        changed[0]['source_sha256'] = hashlib.sha256(changed[0]['source'].encode('utf-8')).hexdigest()
        variants.append(changed)
        for cases in variants:
            with self.subTest(ids=[r['id'] for r in cases]):
                self.rejected(values={CASES: cases})
        # Even consistent aggregate edits cannot shrink the registered population.
        summary = deepcopy(self.data[SUMMARY]); summary['source_inputs'] -= 1
        registration = deepcopy(self.data[REGISTRATION]); registration['source_inputs'] -= 1
        self.rejected(values={CASES: original[:-1], SUMMARY: summary, REGISTRATION: registration}, export=True)

    def test_pair_input_and_raw_populations_are_unique_and_exact(self):
        for path in (RECORDS, INPUTS):
            original = self.data[path]
            unexpected = deepcopy(original); unexpected[0]['id'] = 'unregistered:0'
            for rows in (original[:-1], original + [original[0]],
                         original[:-1] + [original[0]], unexpected):
                with self.subTest(path=path.name, ids=[r['id'] for r in rows]):
                    self.rejected(values={path: rows})
        for version in verifier.RELEASES:
            original = json.loads(self.raw[version]['stdout'])
            unexpected = deepcopy(original); unexpected[0]['id'] = 'unregistered:0'
            for rows in ([], original[:-1], original + [original[0]],
                         original[:-1] + [original[0]], unexpected):
                with self.subTest(release=version, size=len(rows)):
                    self.rejected(values=self.raw_values(version, rows))

    def test_coordinated_hybrid_renaming_cannot_rebind_raw_results(self):
        records, inputs = deepcopy(self.data[RECORDS]), deepcopy(self.data[INPUTS])
        old = records[0]['hybrids'][0]['id']; new = old + ':renamed'
        records[0]['hybrids'][0]['id'] = new
        for row in inputs:
            if row['id'] == old: row['id'] = new
        values = {RECORDS: records, INPUTS: inputs}
        for version in verifier.RELEASES:
            rows = json.loads(self.raw[version]['stdout'])
            for row in rows:
                if row['id'] == old: row['id'] = new
            values.update(self.raw_values(version, rows))
        self.rejected(values=values, export=True)

    def test_source_and_diagnostic_correspondence_cannot_be_bypassed(self):
        inputs = deepcopy(self.data[INPUTS]); inputs[0]['source'] += '# changed\n'
        self.rejected(values={INPUTS: inputs})
        records = deepcopy(self.data[RECORDS]); records[0]['before'] += '# changed\n'
        self.rejected(values={RECORDS: records})
        records = deepcopy(self.data[RECORDS]); records[0]['hybrids'][0]['native']['2.1.1'] = [[999, 0]]
        self.rejected(values={RECORDS: records})
        rows = json.loads(self.raw['2.1.1']['stdout']); rows[0]['diagnostics'] = [[999, 0]]
        self.rejected(values=self.raw_values('2.1.1', rows), export=True)

    def test_diagnostic_coordinates_cannot_use_boolean_or_numeric_coercion(self):
        for bad in (None, '[]', [[True, 0]], [[1.0, 0]], [[1, False]],
                    [[0, 0]], [[1, -1]], [[1]], [[1, 0, 0]]):
            rows = json.loads(self.raw['2.1.1']['stdout']); rows[0]['diagnostics'] = bad
            with self.subTest(diagnostics=bad):
                self.rejected(values=self.raw_values('2.1.1', rows))

    def test_duplicate_json_fields_and_nonfinite_values_are_not_compressed_away(self):
        text = json.dumps(self.data[SUMMARY])
        self.rejected(texts={SUMMARY: '{"source_inputs":32,' + text[1:]}, export=True)
        raw = deepcopy(self.raw['2.1.1'])
        rows = json.loads(raw['stdout'])
        first = json.dumps(rows[0])
        raw['stdout'] = '[{"id":"unregistered:0",' + first[1:] + ',' + ','.join(json.dumps(r) for r in rows[1:]) + ']'
        self.rejected(values={CAPTURE / 'raw-2.1.1.json': raw})
        self.rejected(texts={SUMMARY: text.replace('"source_inputs": 31', '"source_inputs": NaN')})


if __name__ == '__main__':
    unittest.main(verbosity=2)
