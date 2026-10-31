"""Execute isolated, licensed Pyflakes wheels on benign source, never source code.

This compares diagnostic values with a finite export, not the upstream checker's
internal complete evidence. It neither patches Pyflakes nor imports the owned
inputs. Inputs are fixed syntactic controls, not independent maintenance cases.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
WHEELS={
    '2.1.1':('pyflakes-2.1.1-py2.py3-none-any.whl','17dbeb2e3f4d772725c777fabc446d5634d1038f234e77343108ce445ea69ce0'),
    '2.2.0':('pyflakes-2.2.0-py2.py3-none-any.whl','0d94e0e05a19e57a99444b6ddcf9a6eb2e5c68d3ca1e98e90707af8152c90a92')
}
OPERANDS=('0','5','10','100',"''","'word'",'True','False','None','()',
          '(5,)','(None,)','(5, True)','((5,),)','((None,), ())')
BOOTSTRAP='''import sys, runpy
wheel, expected, source = sys.argv[1:]
sys.path.insert(0, wheel)
import pyflakes
origin = pyflakes.__file__.replace(chr(92), '/')
prefix = wheel.replace(chr(92), '/') + '/'
if pyflakes.__version__ != expected or not origin.startswith(prefix):
    raise RuntimeError('the verified wheel was not imported')
sys.argv = ['pyflakes', source]
runpy.run_module('pyflakes', run_name='__main__')
'''
def digest(data):return hashlib.sha256(data).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def program(operand,operator):return 'x = 5\nif x '+operator+' '+operand+':\n    pass\n'
def registered_inputs():
    cases=json.loads((ROOT/'data/pyflakes-upgrade.json').read_text(encoding='utf-8'))['cases']
    texts={program(operand,operator) for operand in OPERANDS for operator in ('is','==')}
    texts.update(case[side] for case in cases for side in ('old_source','new_source'))
    return sorted(texts),cases
def diagnostic(run,input_name):
    """Refuse crashes, unrelated messages, warnings on stderr or invalid exits."""
    require(run.returncode in (0,1),'analyzer failed, not a diagnostic observation')
    require(not run.stderr.strip(),'unexpected analyzer stderr')
    lines=run.stdout.splitlines()
    require(len(lines)<=1,'unexpected multiple diagnostics')
    normalized=[]
    for line in lines:
        prefix=input_name+':'
        require(line.startswith(prefix),'diagnostic source identity differs')
        match=re.fullmatch(r'(\d+)(?::(\d+))?:? (.+)',line[len(prefix):])
        require(match is not None,'unrecognized diagnostic format')
        message=match[3]
        require(message.startswith('use ==/!= to compare'),'unexpected diagnostic kind')
        require(int(match[1])==2,'diagnostic not on registered comparison')
        normalized.append(dict(line=int(match[1]),column=int(match[2]) if match[2] else None,message=message))
    require(run.returncode==len(normalized),'diagnostic exit/output contradiction')
    return normalized
def prepare_wheel(version,directory,fetch):
    filename,expected=WHEELS[version];path=directory/filename
    url='https://pypi.org/pypi/pyflakes/'+version+'/json'
    acquisition=None
    if not path.exists():
        require(fetch,'missing wheel; provide --wheel-dir or explicitly --fetch')
        with urllib.request.urlopen(url,timeout=20) as response:metadata=json.load(response)
        row=next(r for r in metadata['urls'] if r['filename']==filename)
        require(row['digests']['sha256']==expected,'registry identity changed')
        require(row['url'].startswith('https://files.pythonhosted.org/'),'unexpected wheel host')
        with urllib.request.urlopen(row['url'],timeout=20) as response:raw=response.read(1000000)
        require(len(raw)==row['size'],'truncated or oversized wheel')
        require(digest(raw)==expected,'downloaded wheel differs')
        directory.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);acquisition=row['url']
    raw=path.read_bytes();require(digest(raw)==expected,'wheel differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        licenses={n:z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('/LICENSE') or n.endswith('/COPYING')}
        require(any('Permission is hereby granted' in text for text in licenses.values()),'required MIT license absent')
        package=next(n for n in z.namelist() if n=='pyflakes/checker.py')
        source_sha=digest(z.read(package))
        test='pyflakes/test/test_is_literal.py'
        test_text=z.read(test).decode('utf-8') if test in z.namelist() else None
    return path,dict(version=version,registry=url,wheel=filename,wheel_sha256=expected,
        wheel_bytes=len(raw),checker_sha256=source_sha,license_texts=licenses,
        fetched_url=acquisition,upstream_tuple_regression_present=bool(test_text and 'def test_is_tuple_constant' in test_text))
def run(wheel_dir,output,fetch=False):
    require(not output.exists(),'use a fresh external output directory')
    require(not output.resolve().is_relative_to(ROOT.resolve()),'results must be outside the artifact during execution')
    texts,cases=registered_inputs();require(len(texts)==31,'registered source set changed')
    output.mkdir(parents=True);observations=[];release_records=[];start=time.monotonic()
    # Read the existing finite export without importing or executing any input.
    sys.path.insert(0,str(ROOT))
    from pyflakes_upgrade_check import extract
    from producer import evaluate_family
    registration=dict(operand_terms=list(OPERANDS),operators=['is','=='],source_count=len(texts),
        source_digests=[digest(t.encode('ascii')) for t in texts],release_versions=list(WHEELS),
        maximum_observations=62,per_observation_timeout_seconds=3,total_wall_limit_seconds=180,
        preregistered_before_observations=True,selection='Fixed controls and the three previously registered endpoint pairs; not held-out natural source sampling')
    (output/'registration.json').write_text(json.dumps(registration,indent=2)+'\n',encoding='utf-8')
    try:
        with tempfile.TemporaryDirectory(prefix='drift-pyflakes-') as work:
            sample=Path(work)/'owned.py'
            for version in WHEELS:
                wheel,record=prepare_wheel(version,wheel_dir,fetch);release_records.append(record)
                for source in texts:
                    require(time.monotonic()-start<180,'wall budget exceeded')
                    sample.write_text(source,encoding='ascii')
                    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
                    observed=subprocess.run([sys.executable,'-I','-S','-B','-c',BOOTSTRAP,
                        str(wheel.resolve()),version,str(sample)],cwd=work,
                        capture_output=True,text=True,env=env,timeout=3)
                    raw_record=dict(release=version,source=source,returncode=observed.returncode,
                        stdout=observed.stdout.replace(str(sample),'<INPUT>'),
                        stderr=observed.stderr.replace(str(sample),'<INPUT>'))
                    with (output/'raw-observations.jsonl').open('a',encoding='utf-8') as stream:
                        stream.write(json.dumps(raw_record,ensure_ascii=False)+'\n')
                    diagnostics=diagnostic(observed,str(sample))
                    model=extract(source,version=='2.2.0')
                    value=evaluate_family(model,'IsLiteral','comparison')['value']
                    require(value in ('T','F'),'unexpected undefined finite value')
                    actual='T' if diagnostics else 'F'
                    row=dict(release=version,source=source,source_sha256=digest(source.encode('ascii')),
                             diagnostics=diagnostics,exit_code=observed.returncode,
                             finite_value=value,released_value=actual,agrees=value==actual)
                    observations.append(row)
                    require(row['agrees'],'released checker contradicts finite export')
        by={(r['release'],r['source']):r for r in observations}
        endpoints=[]
        for case in cases:
            values=[by[(version,case[side])]['released_value'] for version,side in
                    [('2.1.1','old_source'),('2.2.0','new_source')]]
            require(values==case['expected_values'],'released endpoint transition differs')
            endpoints.append(dict(id=case['id'],values=values,expected=case['expected_values'],provenance=case['provenance']))
        status='PASS'
    except Exception as error:
        status='FAILED_OR_PARTIAL'
        (output/'failure.json').write_text(json.dumps(dict(type=type(error).__name__,message=str(error)),indent=2)+'\n',encoding='utf-8')
        raise
    finally:
        report=dict(status=locals().get('status','FAILED_OR_PARTIAL'),registration=registration,
            scope='Actual released analyzer parsing on fixed benign sources; no source execution, historical environment, natural maintenance cohort, complete upstream evidence or measured user benefit',
            python=dict(version=platform.python_version(),implementation=platform.python_implementation()),
            releases=release_records,observations=observations,endpoints=locals().get('endpoints',[]),
            input_cells_observed=len(observations),mismatches=sum(not r['agrees'] for r in observations),
            boundary='Diagnostic values are compared. The finite normalizer is a semantic encoding, not an exported Pyflakes interface. Scalar and tuple observations can share one source operand; arbitrary coordinate hybrids need not be source-realizable.',
            source_bindings={'integration/pyflakes_release.py':digest(Path(__file__).read_bytes())},
            performance_claim=False)
        report['source_bindings'].update({name:digest((ROOT/name).read_bytes()) for name in
            ['pyflakes_upgrade_check.py','data/pyflakes-upgrade.json','src/producer.py','src/checker.py']})
        (output/'observations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--wheel-dir',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--fetch',action='store_true')
    args=ap.parse_args();report=run(args.wheel_dir,args.output,args.fetch)
    print(json.dumps({k:report[k] for k in ('status','input_cells_observed','mismatches','python')}))
