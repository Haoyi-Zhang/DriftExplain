from __future__ import annotations
import ast, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'abstract_model_check.py'

class AbstractModelCheckTests(unittest.TestCase):
    def test_model_checker_has_no_project_imports(self):
        tree=ast.parse(SCRIPT.read_text())
        imported=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import): imported += [a.name.split('.')[0] for a in n.names]
            elif isinstance(n,ast.ImportFrom) and n.module: imported.append(n.module.split('.')[0])
        self.assertTrue(set(imported) <= {'__future__','itertools','argparse','json','pathlib'})

    def test_bounded_model_check_and_negative_controls(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out.json'
            cp=subprocess.run([sys.executable,str(SCRIPT),'--output',str(out)],cwd=ROOT,text=True,capture_output=True,check=True)
            data=json.loads(out.read_text())
            self.assertEqual(data['status'],'PASS')
            self.assertEqual(data['totals']['counterexamples'],0)
            self.assertGreater(data['totals']['subset_replays'],1000)
            self.assertTrue(data['negative_controls_passed'])

if __name__=='__main__': unittest.main()
