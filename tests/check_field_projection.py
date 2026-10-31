"""Strong same-information projection on field-sensitive theorem boundaries."""
import copy
from itertools import combinations
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import producer
import checker


def base():
    return dict(targets=[dict(anchor='site', raw={'u':'T', 'v':'T'},
                              origins={'u':'old-u', 'v':'old-v'})],
                normalizer={'fact':['u','v']},
                rules=[dict(id='r', family='f', requires=['fact'], forbids=[])])


class FieldProjectionTests(unittest.TestCase):
    def compare(self, before, after, expected):
        cert = producer.make_certificate(before, after, 'f', 'site')
        self.assertEqual(cert['witness'], expected)
        for receive in (checker.check_certificate, checker.check_candidate_certificate,
                        checker.check_structural_certificate):
            self.assertEqual(receive(before, after, cert), (True, 'accepted'))
        delta = producer.compute_delta(before, after)
        final = checker._family_result(after, 'f', 'site')
        for size in range(len(delta)+1):
            for selected in combinations(delta, size):
                ids = [a['id'] for a in selected]
                self.assertEqual(checker._family_result(checker._patch(before, selected), 'f', 'site') == final,
                                 set(expected) <= set(ids))
                candidate = dict(cert, witness=ids)
                self.assertEqual(checker.check_structural_certificate(before, after, candidate)[0], ids == expected)

    def test_metadata_only_rule_edit_has_empty_projected_footprint(self):
        old = base(); new = copy.deepcopy(old)
        new['rules'][0]['description'] = 'excluded documentation'
        self.assertEqual(len(producer.compute_delta(old, new)), 1)
        self.compare(old, new, [])

    def test_dominated_alias_origin_remains_complete_evidence(self):
        old = base(); new = copy.deepcopy(old)
        new['targets'][0]['origins']['v'] = 'new-v'
        self.compare(old, new, ['program|site|v'])

    def test_order_and_sparse_rule_move_remain_observable(self):
        old = base(); new = copy.deepcopy(old)
        new['normalizer']['fact'].reverse()
        self.compare(old, new, ['normalizer|fact'])
        new = copy.deepcopy(old); new['rules'][0]['family'] = 'g'
        self.compare(old, new, ['rule|r'])

    def test_target_absence_hides_lower_read_changes(self):
        old = base(); new = copy.deepcopy(old)
        new['targets'] = []; new['normalizer']['fact'].reverse()
        self.compare(old, new, ['target|site'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
