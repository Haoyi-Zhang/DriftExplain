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
def run():
    path=ROOT/'results/source-pairs'
    registration=json.loads((path/'registration.json').read_text())
    for rel,digest in registration['source_bindings'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise ValueError('execution source differs')
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
    by={r['id']:r for r in inputs};count=0;targets=0
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
        for packet in row['certificates']:
            if not check_pair_certificate(row['before'],row['after'],'2.1.1','2.2.0',packet)[0]:raise ValueError('source certificate')
            anchor=packet['certificate']['candidate']['anchor'];final=producer.evaluate_family(pair.after.model,'IsLiteral',anchor)
            for h in row['hybrids']:
                source,release,frame=pair.hybrid(h['selected'])
                if by[h['id']]['source']!=source or h['source']!=source or h['release']!=release:raise ValueError('hybrid source bytes')
                if (producer.evaluate_family(frame.model,'IsLiteral',anchor)==final)!=(set(packet['source_support'])<=set(h['selected'])):raise ValueError('block support not exact')
                count+=1
                for version in native:
                    ex=export_source(source,version)
                    wanted=[[loc['line'],loc['column']] for loc in ex['locations'] if producer.evaluate_family(ex['model'],'IsLiteral',loc['anchor'])['value']=='T']
                    if Counter(map(tuple,wanted))!=Counter(map(tuple,native[version][h['id']])) or h['native'][version]!=native[version][h['id']]:raise ValueError('retained native disagreement')
            targets+=1
    summary=json.loads((path/'summary.json').read_text())
    if (len(rows),len(by),count,targets)!=(summary['admitted_pairs'],summary['source_realizable_hybrids'],summary['exact_support_subset_checks'],summary['source_certificate_targets']):raise ValueError('summary differs')
    print(json.dumps(dict(status='PASS',source_pairs=len(rows),realizable_hybrids=len(by),native_observations=2*len(by))))
if __name__=='__main__':run()
