from __future__ import annotations
import ast,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'monotone_core_check.py'
class MonotoneCoreCheckTests(unittest.TestCase):
    def test_independent_imports(self):
        tree=ast.parse(SCRIPT.read_text());mods=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):mods += [a.name.split('.')[0] for a in n.names]
            elif isinstance(n,ast.ImportFrom) and n.module:mods.append(n.module.split('.')[0])
        self.assertTrue(set(mods)<={'__future__','argparse','json','pathlib'})
    def test_all_monotone_predicates_through_four_atoms(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out.json'
            subprocess.run([sys.executable,str(SCRIPT),'--max-atoms','4','--output',str(out)],cwd=ROOT,check=True,capture_output=True,text=True)
            d=json.loads(out.read_text())
            self.assertEqual(d['status'],'PASS')
            self.assertEqual(d['totals']['counterexamples'],0)
            self.assertGreaterEqual(d['totals']['upward_predicates'],168)
if __name__=='__main__':unittest.main()
