# Released-analyzer comparison

The Pyflakes comparison invokes the actual unmodified 2.1.1 and 2.2.0 wheels
published on PyPI. Each wheel is content-bound and its MIT permission checked
before use. Wheels remain external prerequisites, not vendored project copies.
The input programs are parsed by the tools, never imported or executed.

The registered set has 31 distinct owned sources, comprising fixed scalar,
singleton, tuple and nested-tuple controls plus the existing three endpoint
pairs. Two releases give 62 diagnostic observations. These are deterministic
controls, not 31 independent projects, a held-out maintenance corpus, or a
population accuracy estimate. The common runtime is CPython 3.12.3; this is not
a claim about the releases' original historical Python environments.

From the artifact root, use a new output directory outside the artifact:

```sh
python -B integration/pyflakes_release.py --wheel-dir /tmp/pyflakes-wheels --output /tmp/pyflakes-observations --fetch
```

Omit `--fetch` to use the already verified external wheels without network
access. No global installation is performed. Each analyzer invocation is limited
to three seconds; the registered matrix has at most 62 invocations and a
180-second aggregate wall limit. Unsupported diagnostic formats, crashes,
unexpected stderr and exit/output contradictions refuse an observation.

For an offline consistency check of the retained capture:

```sh
python -B integration/verify_pyflakes_release.py
python -B tests/check_pyflakes_release.py
```

The offline check rederives values from captured raw output; it does not claim
to rerun the upstream tools. This comparison checks diagnostic values, not an
upstream complete-evidence API. In particular, scalar and tuple observations
can share one source operand: arbitrary independently edited finite coordinates
need not correspond to realizable source edits. The separate source-composition
premises remain necessary.
