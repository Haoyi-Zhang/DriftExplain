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

RELEASES = ('2.1.1', '2.2.0')
# Explicit population from the retained cases.json, not inferred from summary
# counts. Bind both identities and source bytes; a coordinated omission or
# renaming of cases, hybrids and raw rows must not redefine the population.
REGISTERED_SOURCES = {
    'test_is_str:0': '9d7252823666b3071815d8c3b4fcb9999481441bbd85c80dd4e416028418d4a2',
    'test_is_bytes:0': '18396d7c4be13cadf0cbd6dc886002ed0d61384475e8e1e801df239f176fa4b2',
    'test_is_unicode:0': 'c51812d95bc92841f390b16abd756f7241791f9835eba04c8d1fc9e876623279',
    'test_is_int:0': 'ca2dbefabf8e77ac48663c12b007ec214d23a729f949734e8f69665cdaab3bc3',
    'test_is_true:0': 'c528d527274047142cf6b5da308498976fab98cbd5e65e0a8a325a2674d3ce0e',
    'test_is_false:0': '7b4343bc5be93ed75651f3d9714667fc48eda2f0bb81e25b10995715f228baa5',
    'test_is_not_str:0': '69d57c4100af2180fdf2b962b632966fefeff130b5858c790d1c847d51f57dce',
    'test_is_not_bytes:0': '202340f1e7e6cb9bb8f82ed6bcd4107bc19e5b3dc510fcfd27b3e79be1e516ef',
    'test_is_not_unicode:0': '66c75fc440193e40536db53d995fb5285805c398728a85c1fef84ae7d1be65a0',
    'test_is_not_int:0': 'c845668f832e9033f38b892dbfc1f1a44c6f40125ef13a41f7a1242d5f535fa4',
    'test_is_not_true:0': '7bfa9df4ca3198e719cfa0d0994bd8446b6f207c17bb79787dd1ca10e91c5c2a',
    'test_is_not_false:0': '3b841812bed6fb7b21e35bb1b4025c59608ba4c179b1e2c6630488837dd48577',
    'test_left_is_str:0': '76f38f90b14015828738c35027b975fa5ee7b80bbfc69e54776c3fa2cf49e23e',
    'test_left_is_bytes:0': '97febcbacdd394fd1fb714944744ccedb60e30600a81ee569ff14f608f81dbcf',
    'test_left_is_unicode:0': '6cafbb4e615218de362acc902b41919695c02e2b180dd682c772b65b8a1c033d',
    'test_left_is_int:0': '9d7fb1f84eef34166c5af186a3d9b949cd479aa1b14423a09a5821074bea41de',
    'test_left_is_true:0': 'd4140ca3bffe6bcb6d712834bae70f92ab54b6de324a0491cb4d8ea0f542851c',
    'test_left_is_false:0': 'b6040a87c5af404a49ae750183dce6bbd85d7d3f2d5b3eff1232dc3c6106f18e',
    'test_left_is_not_str:0': 'fc4cec96b6efe1be3b544df56aacd7066a1a45745551086f8619f4dcf0e28d86',
    'test_left_is_not_bytes:0': 'fa9cc2b8f5e9e6f26a8cda743546be70dc789985a8d923f83871305e99ce12de',
    'test_left_is_not_unicode:0': '53d7ee4b8f3b27711ce2f256961c2a7280af3a87f40df2f2920a14fe73ddad46',
    'test_left_is_not_int:0': 'aed77f1509cf22f35579cc68b85e8cb5e2d68a4cc32848f830932880ce4d4289',
    'test_left_is_not_true:0': '7b867e19bd472e8ad34ca04fa09502938ae92d321de6f3b3978a3934a6b6a8bf',
    'test_left_is_not_false:0': '5562229389a0d9fb49e1de4085c82d6374180ba1eb11e2ab6ec5a0fdf57b8617',
    'test_chained_operators_is_true:0': '540b1acba255073ae3ceccf05ca2d5317f3f518ba3db5abd07c0bdd5a96fb8c1',
    'test_chained_operators_is_str:0': '55611f2c2df46a71a9a897ddc8224a708a4db920103de8ae4827a48f059329d1',
    'test_chained_operators_is_true_end:0': 'bb8b5a6ff605e1d50077bf64c39e081ea34f832cd09fe0eabc81ff4c5ccf494d',
    'test_chained_operators_is_str_end:0': 'f23c8de902d78e1365841114aa77dcc63ad7408ace8fddc487241f12c0958a18',
    'test_is_tuple_constant:0': '76f2f5781388ee0ab44d4061ca107b524425ceb9d8e4d202ae9baa092e0d3151',
    'test_is_tuple_constant_containing_constants:0': 'e966ced283e3b5e4528bc705701708145913fab4370032ff3f1319dc4428ce10',
    'test_is_tuple_containing_variables_ok:0': '63675257dbed50eeff079a0ed753ca1b2ed6d7ce1d5f91006b733dd0f4ff84b3',
}
TEST_SOURCE_SHA256 = 'a63f570923919b3159e9f3918f5dbf1c6b6158fe9137930f7a8ca3de4af0571b'
REQUIRED_EVIDENCE = (
    'results/source_consumer/cases.json',
    'results/source-pairs/registration.json',
    'results/source-pairs/records.json',
    'results/source-pairs/native-inputs.json',
    'results/source-pairs/raw-2.1.1.json',
    'results/source-pairs/raw-2.2.0.json',
    'results/source-pairs/summary.json',
)
COUNT_FIELDS = (
    'source_inputs', 'admitted_pairs', 'excluded_pairs',
    'source_realizable_hybrids', 'native_parse_observations',
    'source_certificate_targets', 'exact_support_subset_checks',
    'native_model_disagreements', 'natural_maintenance_commits',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field: ' + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('nonfinite JSON value: ' + value)


def parse_json(text):
    return json.loads(text, object_pairs_hook=unique_object,
                      parse_constant=invalid_constant)


def read_json(path):
    try:
        return parse_json(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError('unreadable required evidence: ' + str(path)) from error


def indexed(rows, label, expected=None):
    require(type(rows) is list and bool(rows), label + ': empty or malformed evidence')
    result = {}
    for row in rows:
        require(type(row) is dict and type(row.get('id')) is str
                and bool(row['id']), label + ': malformed identity')
        require(row['id'] not in result, label + ': duplicate identity')
        result[row['id']] = row
    if expected is not None:
        require(set(result) == set(expected), label + ': identity population differs')
    return result


def diagnostics(value):
    # Empty diagnostics are genuine negative findings, not empty evidence.
    require(type(value) is list, 'malformed native diagnostics')
    for location in value:
        require(type(location) is list and len(location) == 2
                and all(type(v) is int for v in location)
                and location[0] >= 1 and location[1] >= 0,
                'malformed native diagnostic location')
    return value


def check_counts(data, expected, label):
    require(type(data) is dict, label + ': malformed counts')
    for key, value in expected.items():
        require(type(data.get(key)) is int and data[key] == value,
                label + ': count differs: ' + key)


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


def verify():
    """Read-only acceptance shared by the CLI and the paper-count exporter.

    No measurement fields are projected away and no nondeterminism exceptions
    apply to these deterministic counts, sources and diagnostic multisets.
    """
    missing = [name for name in REQUIRED_EVIDENCE if not (ROOT / name).is_file()]
    require(not missing, 'missing required evidence: ' + ', '.join(missing))
    path=ROOT/'results/source-pairs'
    registration=read_json(path/'registration.json')
    require(type(registration) is dict, 'malformed registration')
    source_changes=verify_source_bindings(registration,path)
    summary=read_json(path/'summary.json')
    require(type(summary) is dict and set(summary) == set(COUNT_FIELDS) | {
        'status', 'application_decisions_or_time_savings_measured'}, 'summary fields differ')
    require(summary['status'] == 'PASS'
            and summary['application_decisions_or_time_savings_measured'] is False,
            'incomplete source-pair results')
    require(all(type(summary[key]) is int and summary[key] >= 0 for key in COUNT_FIELDS),
            'malformed summary count')
    check_counts(summary, {'native_model_disagreements': 0, 'natural_maintenance_commits': 0}, 'summary')
    originals=read_json(ROOT/'results/source_consumer/cases.json')
    indexed(originals, 'original cases', REGISTERED_SOURCES)
    for old in originals:
        require(type(old.get('source')) is str and bool(old['source']), 'malformed case source')
        digest = hashlib.sha256(old['source'].encode('utf-8')).hexdigest()
        require(digest == old.get('source_sha256') == REGISTERED_SOURCES[old['id']],
                'registered case source identity differs')
        require(old.get('provenance') == 'pyflakes/test/test_is_literal.py'
                and old.get('test_function') == old['id'].rsplit(':', 1)[0],
                'registered case provenance differs')
    check_counts(summary, {'source_inputs': len(originals)}, 'summary')
    check_counts(registration, {'source_inputs': len(originals)}, 'registration')
    require(registration.get('test_source_sha256') == TEST_SOURCE_SHA256,
            'registered upstream test source differs')
    expected=[];excluded=[]
    for old in originals:
        try:pair=SourcePair(old['source'],edited(old['source']),'2.1.1','2.2.0')
        except (ValueError,SyntaxError) as exc:excluded.append(dict(id=old['id'],reason=str(exc)))
        else:expected.append(old)
    if excluded!=registration['excluded']:raise ValueError('exclusion census differs')
    check_counts(registration, {'admitted': len(expected)}, 'registration')
    check_counts(summary, {'admitted_pairs': len(expected), 'excluded_pairs': len(excluded)}, 'summary')
    rows=read_json(path/'records.json')
    indexed(rows, 'source pairs', (r['id'] for r in expected))
    if [r['id'] for r in rows]!=[r['id'] for r in expected]:raise ValueError('pair coverage')
    inputs=read_json(path/'native-inputs.json')
    by=indexed(inputs, 'native inputs');count=0;targets=0;native_count=0;hybrid_ids=[]
    require(all(type(r.get('source')) is str and bool(r['source']) for r in inputs),
            'malformed native input source')
    native={}
    for version in RELEASES:
        raw=read_json(path/('raw-'+version+'.json'))
        require(type(raw) is dict and set(raw) == {'returncode', 'stdout', 'stderr'},
                'malformed native process receipt')
        require(type(raw['returncode']) is int and raw['returncode'] == 0
                and type(raw['stderr']) is str and not raw['stderr'].strip()
                and type(raw['stdout']) is str and bool(raw['stdout'].strip()),
                'failed or malformed native observation')
        observations=parse_json(raw['stdout'])
        indexed(observations, 'native observations', by)
        for observation in observations:diagnostics(observation.get('diagnostics'))
        native[version]={r['id']:r['diagnostics'] for r in observations}
    for old,row in zip(expected,rows,strict=True):
        if row['before']!=old['source'] or row['after']!=edited(old['source']):raise ValueError('source identity differs')
        pair=SourcePair(row['before'],row['after'],'2.1.1','2.2.0');keys=list(pair.blocks)
        subsets=[list(c) for n in range(len(keys)+1) for c in combinations(keys,n)]
        indexed(row['hybrids'], 'pair hybrids',
                (row['id'] + ':hybrid:' + str(i) for i in range(len(subsets))))
        if [r['selected'] for r in row['hybrids']]!=subsets or row['binding']!=pair.binding():raise ValueError('block/subset coverage')
        # Native/source checks are per hybrid, never per submitted certificate.
        # A missing certificate must not suppress its source/native validation.
        frames=[]
        for index,h in enumerate(row['hybrids']):
            require(h['id'] == row['id'] + ':hybrid:' + str(index), 'hybrid identity correspondence')
            source,release,frame=pair.hybrid(h['selected'])
            if h['id'] not in by or by[h['id']]['source']!=source or h['source']!=source or h['release']!=release:
                raise ValueError('hybrid source bytes')
            hybrid_ids.append(h['id'])
            require(type(h.get('native')) is dict and set(h['native']) == set(RELEASES),
                    'hybrid native release coverage')
            for version in native:
                diagnostics(h['native'][version])
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
    totals=dict(source_inputs=len(originals),admitted_pairs=len(rows),excluded_pairs=len(excluded),
        source_realizable_hybrids=len(by),native_parse_observations=native_count,
        exact_support_subset_checks=count,source_certificate_targets=targets,
        native_model_disagreements=0,natural_maintenance_commits=0)
    check_counts(summary, totals, 'summary')
    return dict(status='PASS',**totals,source_pairs=len(rows),realizable_hybrids=len(by),native_observations=native_count,
        measured_sources_differ_from_current=source_changes,scope='Current data-only reconstruction against preserved measured-source identities; not a fresh analyzer execution')


def run():
    result=verify()
    print(json.dumps(result))
    return result
if __name__=='__main__':run()
