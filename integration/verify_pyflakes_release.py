"""Read-only rederivation of retained released-tool observations, no downloads.

Checks actual captured output against current source/finite consumers. It is not
a rerun of the upstream tools and does not turn controlled inputs into a corpus.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_consumer',ROOT/'integration/pyflakes_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
def require(value,message):
    if not value:raise ValueError(message)
def verify(directory):
    report=json.loads((directory/'observations.json').read_text(encoding='utf-8'))
    registration=json.loads((directory/'registration.json').read_text(encoding='utf-8'))
    raw=[json.loads(line) for line in (directory/'raw-observations.jsonl').read_text(encoding='utf-8').splitlines()]
    require(report['status']=='PASS','retained run did not pass')
    require(registration==report['registration'],'registration differs')
    inputs,cases=release.registered_inputs()
    expected={(version,source) for version in release.WHEELS for source in inputs}
    require(len(expected)==62 and len(raw)==62 and len(report['observations'])==62,'incomplete observation matrix')
    require(set(registration['source_digests'])=={release.digest(s.encode('ascii')) for s in inputs},'registered input set differs')
    expected_bindings={'integration/pyflakes_release.py','pyflakes_upgrade_check.py',
                       'data/pyflakes-upgrade.json','src/producer.py','src/checker.py'}
    require(set(report['source_bindings'])==expected_bindings,'required source bindings missing or substituted')
    for path,digest in report['source_bindings'].items():
        source=(ROOT/path).resolve()
        require(source.is_relative_to(ROOT.resolve()),'source binding escapes artifact')
        require(hashlib.sha256(source.read_bytes()).hexdigest()==digest,'current source binding differs: '+path)
    by={};observed={}
    sys.path.insert(0,str(ROOT))
    from pyflakes_upgrade_check import extract
    from producer import evaluate_family
    for item in raw:
        key=(item['release'],item['source'])
        require(key in expected and key not in by,'unexpected or duplicate raw observation')
        diagnostic=release.diagnostic(SimpleNamespace(**{k:item[k] for k in ('returncode','stdout','stderr')}),'<INPUT>')
        finite=evaluate_family(extract(item['source'],item['release']=='2.2.0'),'IsLiteral','comparison')['value']
        actual='T' if diagnostic else 'F'
        require(finite==actual,'released observation contradicts finite export')
        by[key]=dict(diagnostics=diagnostic,exit_code=item['returncode'],finite_value=finite,released_value=actual)
    require(set(by)==expected,'raw matrix incomplete')
    for item in report['observations']:
        key=(item['release'],item['source']);require(key in by and key not in observed,'unexpected or duplicate summary cell')
        require(all(item[k]==v for k,v in by[key].items()) and item['agrees'],'summary cell not supported by captured output')
        require(item['source_sha256']==release.digest(item['source'].encode('ascii')),'source identity differs')
        observed[key]=item
    require(set(observed)==expected,'summary matrix incomplete')
    require(len(report['releases'])==2,'release provenance incomplete')
    for item in report['releases']:
        require(item['version'] in release.WHEELS,'unexpected release')
        filename,digest=release.WHEELS[item['version']]
        require(item['wheel']==filename and item['wheel_sha256']==digest,'release identity differs')
        require(any('Permission is hereby granted' in s for s in item['license_texts'].values()),'license record missing')
    require({r['version'] for r in report['releases']}==set(release.WHEELS),'duplicate release provenance')
    for item,case in zip(report['endpoints'],cases):
        values=[observed[(v,case[s])]['released_value'] for v,s in [('2.1.1','old_source'),('2.2.0','new_source')]]
        require(item['id']==case['id'] and item['values']==case['expected_values']==values,'endpoint transition differs')
    require(len(report['endpoints'])==3 and report['input_cells_observed']==62 and report['mismatches']==0,'invalid report totals')
    return dict(status='PASS',released_cells_rederived=62,unique_owned_sources=31,existing_endpoint_pairs=3,
        actual_upstream_tools_rerun=False,scope='Current consumer and captured-output consistency; not independent sampling or historical-platform certification')
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=ROOT/'results/pyflakes-release')
    print(json.dumps(verify(ap.parse_args().directory)))
