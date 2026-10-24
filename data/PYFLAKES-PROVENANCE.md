# Literal-identity rule upgrade

Read 2026-10-24 from the tagged PyCQA upstream sources linked in
`pyflakes-upgrade.json`. Pyflakes 2.2.0 NEWS documents tuple-comparison warnings.
In 2.1.1 `Checker.COMPARE` tests identity operators against `ast.Str`, `ast.Num`
and `ast.Bytes`. In 2.2.0 it calls `_is_const_non_singleton`: `_is_constant`
recursively admits constant tuples, while `_is_singleton` excludes bool, None
and Ellipsis. `test_is_tuple_constant` supplies the unchanged tuple input;
`test_is_int` supplies the scalar input. Upstream's test also distinguishes
constant tuples from `(x,)`, which is not constant.

`pyflakes_upgrade_check.py` is our reviewed, bounded reimplementation of these
predicates on a declared AST grammar. No upstream package is installed,
imported or executed. It parses source and exports the predicate evolution as
an alias-map change; Pyflakes itself did not use this alias-map interface.
The exporter supplies complete evidence that upstream diagnostics do not expose.
The assignment's value is deliberately outside the comparison read set.

The first replay is a real released rule upgrade on an upstream regression
input. The other two source transitions are owned compositions, not retrieved
commits, independent maintenance histories, or user-study observations. The
review actions are consequences of the replay records, not measured human
decisions. Every subset is checked in the finite exported model; this does not
claim that arbitrary hybrid analyzer implementations exist as released versions.

The short upstream input fragments are retained under its MIT license:

Copyright 2005-2011 Divmod, Inc.
Copyright 2013-2014 Florent Xicluna

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
