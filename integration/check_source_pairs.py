"""Re-derive source block claims against retained original analyzer observations."""
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'integration')]
from source_pair import SourcePair,check_pair_certificate
from source_pair_study import edited
from pyflakes_source import export_source
from collections import Counter
import producer

MEASURED_SOURCE_BINDINGS = {
    'integration/pyflakes_source.py': '285e262c4b9d6c43c8d9565b2ef226af2985d1d235f11c42cd76a08cefefb66c',
    'integration/source_pair.py': '45802405664f22c2f704a9e29e64f3889b5ba842e44c36c49ae31fba02af1fc1',
    'integration/source_pair_study.py': '62ecd8279a9ceaae80df9f548dc2428298816fafa2ba85b36f8cce8f4307499d',
    'src/checker.py': 'e8d1f54d676db1eaefaadc2ef231ee6c7a83cb720248e6a4adae77aa93ff8f7a',
    'src/producer.py': 'e4ab101435f6d89fd6f228e8769301ffc5de35b2649249235223782484420a20',
}
# These two measured implementations were replaced before this repair. Their
# original captured bytes, not a newly rebound current digest, are mandatory.
CAPTURED_PREIMAGES = frozenset(('integration/pyflakes_source.py', 'integration/source_pair.py'))


def verify_source_bindings(registration, path):
    bindings = registration.get('source_bindings')
    if not isinstance(bindings, dict) or set(bindings) != set(MEASURED_SOURCE_BINDINGS):
        raise ValueError('required source binding set differs')
    if bindings != MEASURED_SOURCE_BINDINGS:
        raise ValueError('measured source binding digest differs')
    source_changes = []
    for rel, digest in MEASURED_SOURCE_BINDINGS.items():
        current = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        captured = path / 'source-preimage' / rel
        if rel in CAPTURED_PREIMAGES or captured.is_file():
            if not captured.is_file() or hashlib.sha256(captured.read_bytes()).hexdigest() != digest:
                raise ValueError('measured source preimage missing or differs')
        elif current != digest:
            # For the three unchanged files, current bytes are the measured
            # preimage only while they still match the original pinned digest.
            raise ValueError('measured source preimage missing or differs')
        if current != digest:
            source_changes.append(rel)
    return source_changes


def run():
    path=ROOT/'results/source-pairs'
    registration=json.loads((path/'registration.json').read_text())
    source_changes=verify_source_bindings(registration,path)
    originals=json.loads((ROOT/'results/source_consumer/cases.json').read_text())
    expected=[];excluded=[]
    for old in originals:
        try:pair=SourcePair(old['source'],edited(old['source']),'2.1.1','2.2.0')
        except (ValueError,SyntaxError) as exc:excluded.append(dict(id=old['id'],reason=str(exc)))
        else:expected.append(old)
    if excluded!=registration['excluded']:raise ValueError('exclusion census differs')
    rows=json.loads((path/'records.json').read_text())
    if [r['id'] for r in rows]!=[r['id'] for r in expected]:raise ValueError('pair coverage')
    inputs=json.loads((path/'native-inputs.json').read_text())
    by={r['id']:r for r in inputs};count=0;targets=0;native_count=0;hybrid_ids=[]
    if len(by)!=len(inputs):raise ValueError('duplicate native input identity')
    native={}
    for version in ('2.1.1','2.2.0'):
        raw=json.loads((path/('raw-'+version+'.json')).read_text())
        if raw['returncode'] or raw['stderr'].strip():raise ValueError('failed native observation')
        observations=json.loads(raw['stdout'])
        if len(observations)!=len(by) or {r['id'] for r in observations}!=set(by):raise ValueError('native coverage')
        native[version]={r['id']:r['diagnostics'] for r in observations}
    for old,row in zip(expected,rows,strict=True):
        if row['before']!=old['source'] or row['after']!=edited(old['source']):raise ValueError('source identity differs')
        pair=SourcePair(row['before'],row['after'],'2.1.1','2.2.0');keys=list(pair.blocks)
        subsets=[list(c) for n in range(len(keys)+1) for c in combinations(keys,n)]
        if [r['selected'] for r in row['hybrids']]!=subsets or row['binding']!=pair.binding():raise ValueError('block/subset coverage')
        # Native/source checks are per hybrid, never per submitted certificate.
        # A missing certificate must not suppress its source/native validation.
        frames=[]
        for h in row['hybrids']:
            source,release,frame=pair.hybrid(h['selected'])
            if h['id'] not in by or by[h['id']]['source']!=source or h['source']!=source or h['release']!=release:
                raise ValueError('hybrid source bytes')
            hybrid_ids.append(h['id'])
            for version in native:
                ex=export_source(source,version)
                wanted=[[loc['line'],loc['column']] for loc in ex['locations'] if producer.evaluate_family(ex['model'],'IsLiteral',loc['anchor'])['value']=='T']
                if Counter(map(tuple,wanted))!=Counter(map(tuple,native[version][h['id']])) or h['native'][version]!=native[version][h['id']]:raise ValueError('retained native disagreement')
                native_count+=1
            frames.append((h,frame))
        expected_candidates={('IsLiteral',target['anchor']) for target in pair.after.model['targets']}
        try:
            if not isinstance(row['certificates'],list):raise ValueError('certificate candidate coverage')
            candidates=[(p['certificate']['candidate']['family'],p['certificate']['candidate']['anchor'])
                        for p in row['certificates']]
            if len(candidates)!=len(set(candidates)) or set(candidates)!=expected_candidates:
                raise ValueError('certificate candidate coverage')
        except (KeyError,TypeError) as error:
            raise ValueError('certificate candidate coverage') from error
        for packet in row['certificates']:
            if not check_pair_certificate(row['before'],row['after'],'2.1.1','2.2.0',packet)[0]:raise ValueError('source certificate')
            anchor=packet['certificate']['candidate']['anchor'];final=producer.evaluate_family(pair.after.model,'IsLiteral',anchor)
            for h,frame in frames:
                if (producer.evaluate_family(frame.model,'IsLiteral',anchor)==final)!=(set(packet['source_support'])<=set(h['selected'])):raise ValueError('block support not exact')
                count+=1
            targets+=1
    if len(hybrid_ids)!=len(set(hybrid_ids)) or set(hybrid_ids)!=set(by):raise ValueError('hybrid input coverage')
    summary=json.loads((path/'summary.json').read_text())
    if (len(rows),len(by),count,targets)!=(summary['admitted_pairs'],summary['source_realizable_hybrids'],summary['exact_support_subset_checks'],summary['source_certificate_targets']):raise ValueError('summary differs')
    if native_count!=summary['native_parse_observations']:raise ValueError('native summary differs')
    result=dict(status='PASS',source_pairs=len(rows),realizable_hybrids=len(by),native_observations=native_count,
        measured_sources_differ_from_current=source_changes,scope='Current data-only reconstruction against preserved measured-source identities; not a fresh analyzer execution')
    print(json.dumps(result))
    return result
if __name__=='__main__':run()
