"""Offline admission controls for the real-release diagnostic consumer."""
import importlib.util
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_consumer',ROOT/'integration/pyflakes_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
spec=importlib.util.spec_from_file_location('release_verifier',ROOT/'integration/verify_pyflakes_release.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
@contextmanager
def captured_copy():
    with tempfile.TemporaryDirectory() as temp:
        directory=Path(temp)
        for p in (ROOT/'results/pyflakes-release').iterdir():
            if p.is_file():shutil.copyfile(p,directory/p.name)
        yield directory
class ReleaseConsumerTests(unittest.TestCase):
    def test_registered_set_has_31_sources_not_independent_cases(self):
        sources,cases=release.registered_inputs()
        self.assertEqual(len(sources),31);self.assertEqual(len(cases),3)
        self.assertEqual(len(set(sources)),31)
    def test_clean_and_warning_observations(self):
        self.assertEqual(release.diagnostic(SimpleNamespace(returncode=0,stdout='',stderr=''),'input.py'),[])
        row=release.diagnostic(SimpleNamespace(returncode=1,stdout='input.py:2:6 use ==/!= to compare constant literals\n',stderr=''),'input.py')
        self.assertEqual(row[0]['line'],2)
        legacy=release.diagnostic(SimpleNamespace(returncode=1,stdout='input.py:2:6: use ==/!= to compare constant literals\n',stderr=''),'input.py')
        self.assertEqual(row,legacy)
        old=release.diagnostic(SimpleNamespace(returncode=1,stdout='input.py:2: use ==/!= to compare str, bytes, and int literals\n',stderr=''),'input.py')
        self.assertIsNone(old[0]['column'])
    def test_crash_cannot_become_absent_warning(self):
        for record in [SimpleNamespace(returncode=2,stdout='',stderr=''),SimpleNamespace(returncode=0,stdout='',stderr='Traceback')]:
            with self.assertRaises(ValueError):release.diagnostic(record,'input.py')
    def test_exit_output_contradiction_refused(self):
        with self.assertRaises(ValueError):release.diagnostic(SimpleNamespace(returncode=1,stdout='',stderr=''),'input.py')
        with self.assertRaises(ValueError):release.diagnostic(SimpleNamespace(returncode=0,stdout='input.py:2:6 use ==/!= to compare constant literals\n',stderr=''),'input.py')
    def test_wrong_file_or_rule_or_location_refused(self):
        for line in ['other.py:2:6 use ==/!= to compare constant literals','input.py:2:6 undefined name x','input.py:3:6 use ==/!= to compare constant literals']:
            with self.assertRaises(ValueError):release.diagnostic(SimpleNamespace(returncode=1,stdout=line+'\n',stderr=''),'input.py')
    def test_complete_capture_rederives_without_tools(self):
        self.assertEqual(verifier.verify(ROOT/'results/pyflakes-release')['released_cells_rederived'],62)
    def test_cannot_drop_source_bindings(self):
        with captured_copy() as directory:
            p=directory/'observations.json';report=json.loads(p.read_text(encoding='utf-8'))
            report['source_bindings']={};p.write_text(json.dumps(report),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'required source bindings'):verifier.verify(directory)
    def test_cannot_omit_or_duplicate_an_observation(self):
        with captured_copy() as directory:
            p=directory/'raw-observations.jsonl';lines=p.read_text(encoding='utf-8').splitlines()
            p.write_text('\n'.join(lines[:-1]+[lines[0]])+'\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'unexpected or duplicate'):verifier.verify(directory)
if __name__=='__main__':unittest.main()
