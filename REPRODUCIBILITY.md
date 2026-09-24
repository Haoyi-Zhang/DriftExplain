# Reproducing the finite artifact

## Requirements

A standard Python 3 installation is sufficient.  The acceptance surface uses
only the Python standard library.  No network, package installation, external
solver, compiler, blockchain service, or model is required.

## Complete verification

Run from the artifact root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python verify_artifact.py
```

Expected final status: `PASS`.  The verifier uses a temporary copy, so it does
not import modules from or write caches into the supplied tree.

## Individual commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python run_tests.py
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python abstract_model_check.py
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python monotone_core_check.py
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python generated_differential_check.py
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python audit_static.py --root .
```

Expected invariants:

- 42 unit/regression tests pass;
- `abstract_model_check.json` reports 6,536 endpoint pairs, 37,048 atom
  partitions, 192,176 subset replays, zero counterexamples, and four successful
  negative controls;
- `monotone_core_check.json` reports 65,814 predicates, 194 upward/full-set
  predicates, 970 theorem checks, and zero counterexamples;
- `generated_differential_check.json` reports 60 generated endpoint pairs, 240
  candidates, 240 accepted certificates, 1,176 exhaustive subset replays, 480
  representation-metamorphism checks, and zero disagreements; and
- the structural audit reports `PASS`.

## Determinism and interpretation

The generated check uses five fixed seeds recorded in its JSON output.  The two
bounded enumerators traverse finite spaces in canonical order.  Their JSON
outputs are deterministic and are compared byte-for-byte by the one-command
verifier.

These checks validate implementation correspondence on bounded finite spaces.
They do not mechanize the proof, authenticate upstream source observations, or
estimate real-world detector accuracy.  There is no fitted model and no train/
test split.  The checks address specification and fixture bias through exhaustive
small domains, generated cases, representation metamorphisms, and failure
controls.

## Preserved but non-reproducible campaign surface

The historical timing/scaling campaign is intentionally not a positive
reproduction target: retained accounting already exceeds the declared campaign
cap.  Its raw files remain available for audit, but no speedup or resource-
closure conclusion is drawn from them.  The nine public-pattern contexts are
also not a source corpus; the consumed artifact inputs are the authored finite
records in `data/public_fixtures.json`.
