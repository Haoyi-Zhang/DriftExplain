"""Execute the unmodified releases on all literal-rule upstream test snippets.

Sources are parsed by the released analyzer, never executed as programs. The
corpus is selected statically before any analyzer output, without filtering on
outcomes. It is an upstream regression corpus, not independent maintenance
projects. Existing 31 authored controls and old empirical budgets are separate.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import textwrap
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT),str(Path(__file__).resolve().parent)]
import checker
import producer
from pyflakes_release import WHEELS, prepare_wheel
from pyflakes_source import export_source, make_source_certificate, check_source_certificate

BOOT = '''import ast, json, sys
wheel, version, cases = sys.argv[1:]
sys.path.insert(0,wheel)
import pyflakes
from pyflakes.checker import Checker
from pyflakes.messages import IsLiteral
if pyflakes.__version__ != version or not pyflakes.__file__.replace(chr(92),'/').startswith(wheel.replace(chr(92),'/')+'/'):
    raise RuntimeError('unverified analyzer origin')
out=[]
for row in json.load(open(cases,encoding='utf-8')):
    c=Checker(ast.parse(row['source']),filename='<INPUT>',withDoctest=False)
    out.append(dict(id=row['id'],diagnostics=sorted([m.lineno,m.col] for m in c.messages if type(m) is IsLiteral),other_diagnostic_count=sum(type(m) is not IsLiteral for m in c.messages)))
print(json.dumps(out))
'''


def run(wheel_dir, out, fetch=False):
    if out.exists() or out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('fresh output outside artifact required')
    prepared = {v:prepare_wheel(v,wheel_dir,fetch) for v in WHEELS}
    path, info = prepared['2.2.0']
    with zipfile.ZipFile(path) as z:
        raw = z.read('pyflakes/test/test_is_literal.py')
    tree = ast.parse(raw.decode('utf-8'))
    cases = []
    for fn in ast.walk(tree):
        if type(fn) is not ast.FunctionDef or not fn.name.startswith('test_'): continue
        calls = [n for n in ast.walk(fn) if type(n) is ast.Call and type(n.func) is ast.Attribute
                 and n.func.attr=='flakes' and n.args and type(n.args[0]) is ast.Constant
                 and type(n.args[0].value) is str]
        for index, call in enumerate(calls):
            source = textwrap.dedent(call.args[0].value).strip()+'\n'
            cases.append(dict(id=fn.name+':'+str(index),source=source,
                source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                provenance='pyflakes/test/test_is_literal.py',test_function=fn.name))
    if not 1 <= len(cases) <= 64: raise ValueError('corpus count bound')
    if len({c['id'] for c in cases}) != len(cases): raise ValueError('duplicate corpus identity')
    out.mkdir(parents=True)
    registration = dict(selection='Every literal-string flakes call in every test_ function of the pinned new-release literal-rule test file',
        test_source_sha256=hashlib.sha256(raw).hexdigest(),cases=len(cases),maximum_cases=64,
        maximum_release_processes=2,per_process_timeout_seconds=30,wall_limit_seconds=120,
        candidate_program_execution=False,source_files_not_changed=True,
        source_matching='identical source; only analyzer policy changes')
    (out/'registration.json').write_text(json.dumps(registration,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8',newline='\n')
    start = time.monotonic(); observations = []; paired = []
    report = dict(status='FAILED_OR_PARTIAL',registration=registration)
    try:
        by = {}
        for version,(wheel,record) in prepared.items():
            if time.monotonic()-start >= 120: raise TimeoutError('corpus wall cap')
            p = subprocess.run([sys.executable,'-I','-S','-B','-c',BOOT,str(wheel.resolve()),version,
                                str((out/'cases.json').resolve())],capture_output=True,text=True,timeout=30)
            (out/('raw-'+version+'.json')).write_text(json.dumps(dict(returncode=p.returncode,
                stdout=p.stdout,stderr=p.stderr),indent=2)+'\n',encoding='utf-8')
            if p.returncode != 0 or p.stderr.strip(): raise ValueError('released analyzer failed')
            values = json.loads(p.stdout)
            if len(values)!=len(cases) or {r['id'] for r in values}!={c['id'] for c in cases}:
                raise ValueError('incomplete or duplicated released output')
            for row in values: by[version,row['id']] = row
            observations.append(record)
        for case in cases:
            exports = {v:export_source(case['source'],v) for v in WHEELS}
            for version,exp in exports.items():
                expected = []
                for loc in exp['locations']:
                    val = producer.evaluate_family(exp['model'],'IsLiteral',loc['anchor'])['value']
                    if val=='T': expected.append([loc['line'],loc['column']])
                actual = by[version,case['id']]['diagnostics']
                if Counter(map(tuple,actual)) != Counter(map(tuple,expected)):
                    raise ValueError('native/whole-source export mismatch: '+case['id']+' '+version)
            old,new = (exports[v]['model'] for v in WHEELS)
            certs = []
            for loc in exports['2.2.0']['locations']:
                cert = make_source_certificate(case['source'],'2.1.1','2.2.0',loc['anchor'])
                verdict = check_source_certificate(case['source'],'2.1.1','2.2.0',cert)
                if not verdict[0]: raise ValueError('source-derived certificate rejects')
                certs.append(cert)
            paired.append(dict(id=case['id'],source_sha256=case['source_sha256'],exports=exports,
                old_diagnostics=by['2.1.1',case['id']]['diagnostics'],
                new_diagnostics=by['2.2.0',case['id']]['diagnostics'],certificates=certs))
        report.update(status='PASS',releases=observations,rows=paired,
            native_parse_observations=2*len(cases),source_cases=len(cases),
            comparison_edges=sum(len(r['certificates']) for r in paired),
            changed_cases=sum(r['old_diagnostics']!=r['new_diagnostics'] for r in paired),
            model_native_disagreements=0,
            scope='Automatically exported comparison family on actual upstream regression snippets; not all diagnostics, a natural maintenance cohort, changed-file matching or measured user utility')
    except BaseException as exc:
        report.update(error=dict(type=type(exc).__name__,message=str(exc)),completed_source_cases=len(paired))
        raise
    finally:
        report['source_bindings']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
            ('integration/pyflakes_source.py','integration/pyflakes_source_study.py','src/producer.py','src/checker.py')}
        (out/'observations.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
        (out/'environment.json').write_text(json.dumps(dict(python=platform.python_version(),
            platform=platform.platform(),elapsed_seconds=time.monotonic()-start),indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wheel-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fetch',action='store_true')
    a=p.parse_args();r=run(a.wheel_dir,a.output,a.fetch)
    print(json.dumps({k:r[k] for k in ('status','source_cases','comparison_edges','native_parse_observations','changed_cases','model_native_disagreements')}))
