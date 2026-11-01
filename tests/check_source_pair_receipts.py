"""Data-only receipt mutations; never write captures or run upstream tools."""
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'integration')]
import check_source_pairs as verifier

CAPTURE = ROOT / 'results/source-pairs'


@contextmanager
def memory_capture(*, json_values=None, missing=(), byte_values=None):
    """Override reads only; original files and captured identities stay intact."""
    texts = {p.resolve(): json.dumps(v) for p, v in (json_values or {}).items()}
    absent = {p.resolve() for p in missing}
    contents = {p.resolve(): v for p, v in (byte_values or {}).items()}
    read_text, read_bytes, is_file = Path.read_text, Path.read_bytes, Path.is_file

    def text(path, *args, **kwargs):
        if path.resolve() in texts:
            return texts[path.resolve()]
        return read_text(path, *args, **kwargs)

    def data(path, *args, **kwargs):
        if path.resolve() in absent:
            raise FileNotFoundError(path)
        if path.resolve() in contents:
            return contents[path.resolve()]
        return read_bytes(path, *args, **kwargs)

    def exists(path):
        return False if path.resolve() in absent else is_file(path)

    with mock.patch.object(Path, 'read_text', text), \
         mock.patch.object(Path, 'read_bytes', data), \
         mock.patch.object(Path, 'is_file', exists):
        yield


class SourcePairReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = json.loads((CAPTURE / 'registration.json').read_text(encoding='utf-8'))
        cls.records = json.loads((CAPTURE / 'records.json').read_text(encoding='utf-8'))

    def run_capture(self):
        with redirect_stdout(io.StringIO()):
            return verifier.run()

    def test_normal_capture_exact_counts_and_original_two_source_differences(self):
        with mock.patch.object(verifier, 'export_source', wraps=verifier.export_source) as exports:
            result = self.run_capture()
        self.assertEqual((result['source_pairs'], result['realizable_hybrids'], result['native_observations']),
                         (27, 108, 216))
        self.assertEqual(exports.call_count, 216)
        self.assertEqual(result['measured_sources_differ_from_current'],
                         ['integration/pyflakes_source.py', 'integration/source_pair.py'])

    def test_missing_certificate_rejected(self):
        records = deepcopy(self.records)
        records[0]['certificates'] = []
        with memory_capture(json_values={CAPTURE / 'records.json': records}):
            with self.assertRaisesRegex(ValueError, 'certificate candidate coverage'):
                self.run_capture()

    def test_duplicate_certificate_rejected(self):
        records = deepcopy(self.records)
        records[0]['certificates'].append(deepcopy(records[0]['certificates'][0]))
        with memory_capture(json_values={CAPTURE / 'records.json': records}):
            with self.assertRaisesRegex(ValueError, 'certificate candidate coverage'):
                self.run_capture()

    def test_missing_plus_duplicate_cannot_preserve_aggregate_coverage(self):
        records = deepcopy(self.records)
        records[0]['certificates'] = []
        records[1]['certificates'].append(deepcopy(records[1]['certificates'][0]))
        with memory_capture(json_values={CAPTURE / 'records.json': records}):
            with self.assertRaisesRegex(ValueError, 'certificate candidate coverage'):
                self.run_capture()

    def test_wrong_candidate_family_or_anchor_rejected(self):
        for key, value in (('family', 'other'), ('anchor', 'other')):
            records = deepcopy(self.records)
            records[0]['certificates'][0]['certificate']['candidate'][key] = value
            with self.subTest(key=key), memory_capture(json_values={CAPTURE / 'records.json': records}):
                with self.assertRaisesRegex(ValueError, 'certificate candidate coverage'):
                    self.run_capture()

    def test_native_check_does_not_depend_on_certificate_list_length(self):
        records = deepcopy(self.records)
        records[0]['certificates'] = []
        records[0]['hybrids'][0]['native']['2.1.1'] = [[999, 0]]
        with memory_capture(json_values={CAPTURE / 'records.json': records}):
            with self.assertRaisesRegex(ValueError, 'retained native disagreement'):
                self.run_capture()

    def test_exact_required_binding_set_rejects_missing_empty_and_extra(self):
        variants = [{}, None]
        for key in self.registration['source_bindings']:
            bindings = dict(self.registration['source_bindings'])
            del bindings[key]
            variants.append(bindings)
        variants.append({**self.registration['source_bindings'], 'unexpected.py': '0' * 64})
        for bindings in variants:
            registration = deepcopy(self.registration)
            registration['source_bindings'] = bindings
            with self.subTest(bindings=bindings), memory_capture(
                    json_values={CAPTURE / 'registration.json': registration}):
                with self.assertRaisesRegex(ValueError, 'required source binding set'):
                    self.run_capture()
        registration = deepcopy(self.registration)
        del registration['source_bindings']
        with memory_capture(json_values={CAPTURE / 'registration.json': registration}):
            with self.assertRaisesRegex(ValueError, 'required source binding set'):
                self.run_capture()

    def test_wrong_original_digest_rejected_for_every_required_binding(self):
        for key in self.registration['source_bindings']:
            registration = deepcopy(self.registration)
            registration['source_bindings'][key] = '0' * 64
            with self.subTest(key=key), memory_capture(json_values={CAPTURE / 'registration.json': registration}):
                with self.assertRaisesRegex(ValueError, 'measured source binding digest'):
                    self.run_capture()

    def test_captured_measurement_cannot_be_rebound_to_current_sources(self):
        for key in verifier.CAPTURED_PREIMAGES:
            registration = deepcopy(self.registration)
            registration['source_bindings'][key] = hashlib.sha256((ROOT / key).read_bytes()).hexdigest()
            self.assertNotEqual(registration['source_bindings'][key], self.registration['source_bindings'][key])
            with self.subTest(key=key), memory_capture(json_values={CAPTURE / 'registration.json': registration}):
                with self.assertRaisesRegex(ValueError, 'measured source binding digest'):
                    self.run_capture()

    def test_each_required_captured_preimage_must_exist_and_match(self):
        for key in verifier.CAPTURED_PREIMAGES:
            path = CAPTURE / 'source-preimage' / key
            with self.subTest(key=key, failure='missing'), memory_capture(missing=[path]):
                with self.assertRaisesRegex(ValueError, 'preimage missing or differs'):
                    self.run_capture()
            with self.subTest(key=key, failure='changed'), memory_capture(byte_values={path: b'wrong preimage'}):
                with self.assertRaisesRegex(ValueError, 'preimage missing or differs'):
                    self.run_capture()
            # Even a current file equal to the measured bytes cannot stand in
            # for deletion of one of the two explicitly retained preimages.
            with self.subTest(key=key, failure='current substituted'), memory_capture(
                    missing=[path], byte_values={ROOT / key: path.read_bytes()}):
                with self.assertRaisesRegex(ValueError, 'preimage missing or differs'):
                    self.run_capture()

    def test_unchanged_measured_sources_still_require_original_bytes(self):
        for key in set(verifier.MEASURED_SOURCE_BINDINGS) - verifier.CAPTURED_PREIMAGES:
            with self.subTest(key=key), memory_capture(byte_values={ROOT / key: b'changed current source'}):
                with self.assertRaisesRegex(ValueError, 'preimage missing or differs'):
                    self.run_capture()


if __name__ == '__main__':
    unittest.main()
