"""Replay the reviewed Pyflakes literal-rule change, without importing Pyflakes.

Upstream predicates are reimplemented for a bounded AST grammar. Source is
parsed only. This is a semantic export of a real rule change, not an upstream
complete-evidence interface or an execution of the full tagged analyzers.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import checker
import producer
from information_paths_check import APIS, measured


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def comparison(source):
    tree = ast.parse(source)
    require(len(tree.body) == 2, "one assignment then one if required")
    assignment, branch = tree.body
    require(isinstance(assignment, ast.Assign) and len(assignment.targets) == 1
            and isinstance(assignment.targets[0], ast.Name)
            and assignment.targets[0].id == "x"
            and isinstance(assignment.value, ast.Constant)
            and type(assignment.value.value) is int, "unsupported assignment")
    require(isinstance(branch, ast.If) and not branch.orelse
            and len(branch.body) == 1 and isinstance(branch.body[0], ast.Pass),
            "unsupported branch")
    node = branch.test
    require(isinstance(node, ast.Compare) and len(node.ops) == 1
            and len(node.comparators) == 1 and isinstance(node.left, ast.Name)
            and node.left.id == "x" and type(node.ops[0]) in (ast.Is, ast.Eq),
            "unsupported comparison")
    def admitted(n):
        return ((isinstance(n, ast.Constant) and type(n.value) in (int, str, bool, type(None)))
                or (isinstance(n, ast.Tuple) and all(admitted(e) for e in n.elts)))
    require(admitted(node.comparators[0]), "unsupported operand")
    return node


def scalar(n):
    return isinstance(n, ast.Constant) and type(n.value) in (int, str, bytes, float, complex)


def tuple_constant(n):
    return isinstance(n, ast.Tuple) and all(
        isinstance(e, ast.Constant) or tuple_constant(e) for e in n.elts)


def tagged_warning(node, new):
    # Translation of COMPARE and (for 2.2.0) _is_const_non_singleton,
    # restricted to the admitted grammar. Assignment values do not affect it.
    right = node.comparators[0]
    return isinstance(node.ops[0], ast.Is) and (scalar(right) or (new and tuple_constant(right)))


def extract(source, new):
    node = comparison(source)
    right = node.comparators[0]
    origin = ast.dump(right, include_attributes=False)
    return {
        "targets": [{"anchor": "comparison", "raw": {
            "identity": "T" if isinstance(node.ops[0], ast.Is) else "F",
            "scalar": "T" if scalar(right) else "F",
            "tuple": "T" if tuple_constant(right) else "F"}, "origins": {
                "identity": ast.dump(node.ops[0]), "scalar": origin, "tuple": origin}}],
        "normalizer": {"identity": ["identity"],
                       "literal": ["scalar", "tuple"] if new else ["scalar"]},
        "rules": [{"id": "IsLiteral", "family": "IsLiteral",
                   "requires": ["identity", "literal"], "forbids": []}]}


def run(output, tex):
    require(not output.exists(), "use a fresh result path")
    inputs = json.loads((ROOT / "data/pyflakes-upgrade.json").read_text(encoding="utf-8"))
    records = []
    for case in inputs["cases"]:
        old, new = extract(case["old_source"], False), extract(case["new_source"], True)
        cert = producer.make_certificate(old, new, "IsLiteral", "comparison")
        values = [cert["old"]["value"], cert["new"]["value"]]
        require(values == case["expected_values"], "endpoint regression")
        for source, current, model in ((case["old_source"], False, old),
                                       (case["new_source"], True, new)):
            require(tagged_warning(comparison(source), current) ==
                    (producer.evaluate_family(model, "IsLiteral", "comparison")["value"] == "T"),
                    "tagged-rule endpoint disagreement")
        changes = producer.compute_delta(old, new)
        exact, value = [], []
        for size in range(len(changes) + 1):
            for subset in itertools.combinations(changes, size):
                hybrid = producer.apply_operations(old, subset)
                result = producer.evaluate_family(hybrid, "IsLiteral", "comparison")
                ids = [c["id"] for c in subset]
                if result["value"] == cert["new"]["value"]:
                    value.append(ids)
                if result == cert["new"]:
                    exact.append(ids)
                require((result == cert["new"]) == set(cert["witness"]).issubset(ids),
                        "principal filter mismatch")
        require(len(cert["witness"]) == case["expected_complete_size"], "support regression")
        measurements = {name: measured(api, old, new, cert) for name, api in APIS.items()}
        require(all(r["decision"] == [True, "accepted"] for r in measurements.values()),
                "checker mismatch")
        # Every support atom is necessary; every supplied subset is classified
        # by all three receiver paths against the exact enumerated oracle.
        for size in range(len(changes) + 1):
            for subset in itertools.combinations(changes, size):
                proposal = deepcopy(cert)
                proposal["witness"] = [c["id"] for c in subset]
                expected = proposal["witness"] == cert["witness"]
                require(all(api(old, new, proposal)[0] == expected for api in APIS.values()),
                        "supplied-subset decision mismatch")
        records.append({**case, "old": old, "new": new, "certificate": cert,
                        "warning_diff": values[0] != values[1],
                        "minimum_value_supports": [s for s in value if len(s) == len(value[0])],
                        "complete_sufficient_subsets": exact, "measurements": measurements})
    report = {"status": "PASS", "scope": "Reviewed predicate replay, not full Pyflakes execution",
              "upstream": {k: v for k, v in inputs.items() if k != "cases"}, "records": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = []
    labels = ("Tuple-policy upgrade", "Operand + policy", "Repair + policy")
    for label, r in zip(labels, records):
        c = r["certificate"]
        m = r["measurements"]
        lines.append(f"{label} & ${c['old']['value']}\\to {c['new']['value']}$ & "
                     f"{len(r['minimum_value_supports'][0])} & {len(c['witness'])} & "
                     + "/".join(str(m[n]["hybrid_replays"]) for n in ("structure", "candidate", "identify"))
                     + r"\\")
    tex.write_text("% Generated by pyflakes_upgrade_check.py from checked replay.\n"
                   + "\n".join(lines) + "\n\\bottomrule\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS", "cases": len(records),
                      "complete_support_sizes": [len(r["certificate"]["witness"]) for r in records]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tex", required=True, type=Path)
    args = parser.parse_args()
    run(args.output, args.tex)
