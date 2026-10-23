"""Owned source-to-evidence study with all source hybrids and native warnings."""
import argparse
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from source_bridge import extract, patch_source, compiler_warnings
from producer import compute_delta, apply_operations, evaluate_family, make_certificate
from checker import check_certificate, check_candidate_certificate, check_structural_certificate

FAMILY = 'identity-literal'


def require(value, description):
    if not value:
        raise ValueError(description)


def run():
    pairs = json.loads((ROOT / 'data/source_bridge_pairs.json').read_text(encoding='utf-8'))
    packets = []
    source_hybrids = candidate_checks = certificate_checks = 0
    for pair in pairs:
        before, after = extract(pair['old']), extract(pair['new'])
        operations = compute_delta(before.model, after.model)
        ids = [item['id'] for item in operations]
        require(len(ids) <= 8, 'bounded source delta exceeded')
        targets = [target['anchor'] for target in after.model['targets']]
        require(before.slots.keys() == after.slots.keys(), 'source identity correspondence differs')
        candidates = []
        for anchor in targets:
            certificate = make_certificate(before.model, after.model, FAMILY, anchor)
            for check in (check_certificate, check_candidate_certificate, check_structural_certificate):
                require(check(before.model, after.model, certificate)[0], 'independent certificate refusal')
                certificate_checks += 1
            candidates.append({'anchor': anchor, 'certificate': certificate,
                               'minimum_value_support': None})
        rows = []
        for size in range(len(operations) + 1):
            for positions in combinations(range(len(operations)), size):
                selected = [operations[index] for index in positions]
                selected_ids = [item['id'] for item in selected]
                hybrid_source = patch_source(before, after, selected_ids)
                extracted = extract(hybrid_source)
                expected = apply_operations(before.model, selected)
                require(extracted.model == expected, 'source patch/extraction does not commute')
                native = compiler_warnings(extracted)
                observed = {item['anchor'] for item in native}
                predicted = {anchor for anchor in targets
                             if evaluate_family(extracted.model, FAMILY, anchor)['value'] == 'T'}
                require(observed == predicted, 'CPython warnings disagree with exported evidence')
                for candidate in candidates:
                    final = candidate['certificate']['new']
                    evidence = evaluate_family(extracted.model, FAMILY, candidate['anchor'])
                    exact = evidence == final
                    contains_support = set(candidate['certificate']['witness']) <= set(selected_ids)
                    require(exact == contains_support, 'source-relative principal filter failed')
                    if evidence['value'] == final['value'] and candidate['minimum_value_support'] is None:
                        candidate['minimum_value_support'] = size
                    candidate_checks += 1
                rows.append({'selected': selected_ids, 'source': hybrid_source,
                             'compiler_warnings': native, 'commutation': True})
                source_hybrids += 1
        packets.append({'name': pair['name'], 'old_source': pair['old'],
                        'new_source': pair['new'], 'delta': operations,
                        'candidates': candidates, 'hybrids': rows})
    return {'scope': 'authored bounded Python identity-comparison source fragment; CPython parses/compiles but no source is executed; not a natural analyzer-upgrade corpus',
            'source_pairs': len(packets), 'source_hybrids': source_hybrids,
            'candidate_subset_checks': candidate_checks,
            'independent_certificate_acceptances': certificate_checks,
            'source_commutation_or_native_warning_or_support_failures': 0,
            'performance_measurement': False,
            'environment': {'python': sys.version, 'implementation': platform.python_implementation()},
            'source_bindings': {name: sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ('src/source_bridge.py', 'source_bridge_check.py',
                                             'data/source_bridge_pairs.json', 'src/producer.py', 'src/checker.py')},
            'packets': packets}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refuse to overwrite an existing result')
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('packets', 'source_bindings', 'environment')}))
