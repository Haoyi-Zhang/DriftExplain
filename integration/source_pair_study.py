"""Realizable source edits on every eligible pinned upstream regression snippet.

Edited partners are authored operator changes, not natural maintenance commits.
Two original analyzers parse these programs; no input program is executed.
"""
import argparse
import ast
from collections import Counter
from copy import deepcopy
import hashlib
from itertools import combinations
import json
from pathlib import Path
import platform
import subprocess
import sys
import textwrap
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'integration')]
from pyflakes_release import WHEELS,prepare_wheel
from pyflakes_source import export_source
from source_pair import SourcePair,make_pair_certificate,check_pair_certificate
import producer

BOOT='''import ast,json,sys
wheel,version,source_file=sys.argv[1:]
sys.path.insert(0,wheel)
import pyflakes
from pyflakes.checker import Checker
from pyflakes.messages import IsLiteral
if pyflakes.__version__!=version or not pyflakes.__file__.startswith(wheel+'/'):raise ValueError('analyzer origin')
rows=[]
for row in json.load(open(source_file,encoding='utf-8')):
 c=Checker(ast.parse(row['source']),filename='<INPUT>',withDoctest=False)
 rows.append(dict(id=row['id'],diagnostics=sorted([m.lineno,m.col] for m in c.messages if type(m) is IsLiteral)))
print(json.dumps(rows))
'''
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources(wheel):
    with zipfile.ZipFile(wheel) as z:raw=z.read('pyflakes/test/test_is_literal.py')
    tree=ast.parse(raw);rows=[]
    for fn in ast.walk(tree):
        if type(fn) is not ast.FunctionDef or not fn.name.startswith('test_'):continue
        calls=[n for n in ast.walk(fn) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='flakes'
               and n.args and type(n.args[0]) is ast.Constant and type(n.args[0].value) is str]
        for i,c in enumerate(calls):rows.append(dict(id=fn.name+':'+str(i),source=textwrap.dedent(c.args[0].value).strip()+'\n'))
    return rows,hashlib.sha256(raw).hexdigest()
def edited(source):
    tree=ast.parse(source);nodes=sorted((n for n in ast.walk(tree) if type(n) is ast.Compare),key=lambda n:(n.lineno,n.col_offset))
    if not nodes:raise ValueError('no comparison')
    n=nodes[0];replacement=deepcopy(n)
    choices={ast.Is:ast.Eq,ast.IsNot:ast.NotEq,ast.Eq:ast.Is,ast.NotEq:ast.IsNot}
    if len(n.ops)!=1 or type(n.ops[0]) not in choices:raise ValueError('first comparison outside fixed operator edit')
    replacement.ops[0]=choices[type(n.ops[0])]()
    lines=source.splitlines(keepends=True);offsets=[0]
    for line in lines:offsets.append(offsets[-1]+len(line))
    a,b=offsets[n.lineno-1]+n.col_offset,offsets[n.end_lineno-1]+n.end_col_offset
    return '# authored operator edit; line displacement is not an evidence atom\n'+source[:a]+ast.unparse(replacement)+source[b:]
def run(wheel_dir,out):
    if out.exists() or out.resolve().is_relative_to(ROOT.resolve()):raise ValueError('new external output required')
    wheels={v:prepare_wheel(v,wheel_dir,False) for v in WHEELS}
    all_cases,test_id=sources(wheels['2.2.0'][0]);admitted=[];excluded=[];inputs=[]
    for row in all_cases:
        try:
            after=edited(row['source']);pair=SourcePair(row['source'],after,'2.1.1','2.2.0')
        except (ValueError,SyntaxError) as exc:
            excluded.append(dict(id=row['id'],reason=str(exc)));continue
        hybrids=[];keys=list(pair.blocks)
        for n in range(len(keys)+1):
            for subset in combinations(keys,n):
                source,release,frame=pair.hybrid(subset)
                ident=row['id']+':hybrid:'+str(len(hybrids))
                inputs.append(dict(id=ident,source=source));hybrids.append(dict(id=ident,selected=list(subset),release=release,source=source))
        admitted.append(dict(id=row['id'],before=row['source'],after=after,binding=pair.binding(),hybrids=hybrids))
    if len(inputs)>512 or len(all_cases)>64:raise ValueError('registered source bound')
    out.mkdir(parents=True)
    save(out/'registration.json',dict(selection='All pinned literal-rule upstream regression string inputs, then outcome-independent fixed syntax admission',
        test_source_sha256=test_id,source_inputs=len(all_cases),admitted=len(admitted),excluded=excluded,
        maximum_input_modules=512,maximum_analyzer_processes=2,per_process_seconds=30,
        edit='Toggle the first single is/is-not/equality operator; prepend one comment line',
        edited_partners_are_authored=True,natural_maintenance_commits=False,
        source_bindings={n:sha(ROOT/n) for n in ('integration/source_pair.py','integration/source_pair_study.py','integration/pyflakes_source.py','src/producer.py','src/checker.py')}))
    save(out/'native-inputs.json',inputs);native={}
    for version,(wheel,record) in wheels.items():
        p=subprocess.run([sys.executable,'-I','-S','-B','-c',BOOT,str(wheel.resolve()),version,str((out/'native-inputs.json').resolve())],
            capture_output=True,text=True,timeout=30)
        save(out/('raw-'+version+'.json'),dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode or p.stderr.strip():raise ValueError('released analyzer failed')
        rows=json.loads(p.stdout)
        if len(rows)!=len(inputs) or {r['id'] for r in rows}!={r['id'] for r in inputs}:raise ValueError('native result coverage')
        native[version]={r['id']:r['diagnostics'] for r in rows}
    checked=0;certificates=0
    for row in admitted:
        pair=SourcePair(row['before'],row['after'],'2.1.1','2.2.0');row['certificates']=[]
        for target in pair.after.model['targets']:
            anchor=target['anchor'];packet=make_pair_certificate(row['before'],row['after'],'2.1.1','2.2.0',anchor)
            if not check_pair_certificate(row['before'],row['after'],'2.1.1','2.2.0',packet)[0]:raise ValueError('source receiver rejects')
            final=producer.evaluate_family(pair.after.model,'IsLiteral',anchor)
            for hybrid in row['hybrids']:
                _,_,export=pair.hybrid(hybrid['selected'])
                exact=producer.evaluate_family(export.model,'IsLiteral',anchor)==final
                if exact!=(set(packet['source_support'])<=set(hybrid['selected'])):raise ValueError('block support differs from realizable hybrids')
                checked+=1
            row['certificates'].append(packet);certificates+=1
        for hybrid in row['hybrids']:
            hybrid['native']={}
            for version in WHEELS:
                export=export_source(hybrid['source'],version)
                expected=[]
                for loc in export['locations']:
                    if producer.evaluate_family(export['model'],'IsLiteral',loc['anchor'])['value']=='T':expected.append([loc['line'],loc['column']])
                actual=native[version][hybrid['id']]
                if Counter(map(tuple,expected))!=Counter(map(tuple,actual)):raise ValueError('native/model diagnostic mismatch')
                hybrid['native'][version]=actual
    save(out/'records.json',admitted)
    summary=dict(status='PASS',source_inputs=len(all_cases),admitted_pairs=len(admitted),excluded_pairs=len(excluded),
        source_realizable_hybrids=len(inputs),native_parse_observations=2*len(inputs),source_certificate_targets=certificates,
        exact_support_subset_checks=checked,native_model_disagreements=0,natural_maintenance_commits=0,
        application_decisions_or_time_savings_measured=False)
    save(out/'summary.json',summary);save(out/'environment.json',dict(python=platform.python_version(),platform=platform.platform()))
    print(json.dumps(summary));return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wheel-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.wheel_dir,a.output)
