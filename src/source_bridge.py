"""Fail-closed source bridge for an owned Python identity-comparison fragment.

Only parse/compile source; never execute it. This is not a general Python or
Solidity analyzer. Stable function names identify one comparison each. Operator
and operand syntax are independently editable observation slots.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import warnings


@dataclass(frozen=True)
class Extracted:
    source: str
    model: dict
    slots: dict
    function_lines: dict


def extract(source: str) -> Extracted:
    if type(source) is not str or not source.isascii() or len(source) > 8192:
        raise ValueError('source must be bounded ASCII text')
    tree = ast.parse(source)
    if not 1 <= len(tree.body) <= 8:
        raise ValueError('expected one to eight functions')
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    targets, slots, function_lines = [], {}, {}
    for function in tree.body:
        if (not isinstance(function, ast.FunctionDef) or function.decorator_list
                or function.returns is not None or function.type_comment is not None
                or getattr(function, 'type_params', ()) or len(function.body) != 1
                or not isinstance(function.body[0], ast.Return)):
            raise ValueError('unsupported function structure')
        args = function.args
        if (args.posonlyargs or len(args.args) != 1 or args.args[0].arg != 'x'
                or args.args[0].annotation is not None or args.vararg or args.kwarg
                or args.kwonlyargs or args.defaults or args.kw_defaults
                or args.args[0].type_comment is not None):
            raise ValueError('expected exactly one unannotated x parameter')
        if function.name in function_lines:
            raise ValueError('duplicate function identity')
        compare = function.body[0].value
        if (not isinstance(compare, ast.Compare) or len(compare.ops) != 1
                or len(compare.comparators) != 1
                or not isinstance(compare.left, ast.Name) or compare.left.id != 'x'
                or type(compare.ops[0]) not in (ast.Is, ast.Eq)):
            raise ValueError('expected x compared with one operand using is or ==')
        right = compare.comparators[0]
        constant = type(right) is ast.Constant and type(right.value) is int and 0 <= right.value <= 100
        if not constant and not (type(right) is ast.Name and right.id == 'x'):
            raise ValueError('operand must be x or an integer in 0..100')
        if compare.lineno != compare.end_lineno:
            raise ValueError('multiline comparisons are outside this fragment')
        anchor = function.name
        function_lines[anchor] = (function.lineno, function.end_lineno)
        targets.append({'anchor': anchor,
                        'raw': {'identity': 'T' if type(compare.ops[0]) is ast.Is else 'F',
                                'constant': 'T' if constant else 'F'},
                        'origins': {'identity': ast.dump(compare.ops[0], include_attributes=False),
                                    'constant': ast.dump(right, include_attributes=False)}})
        line = offsets[compare.lineno - 1]
        slots['program|' + anchor + '|identity'] = (
            line + compare.left.end_col_offset, line + right.col_offset)
        slots['program|' + anchor + '|constant'] = (
            line + right.col_offset, line + right.end_col_offset)
    model = {'targets': sorted(targets, key=lambda item: item['anchor']),
             'normalizer': {'identity_operator': ['identity'], 'constant_operand': ['constant']},
             'rules': [{'id': 'identity-literal', 'family': 'identity-literal',
                        'requires': ['identity_operator', 'constant_operand'], 'forbids': []}]}
    return Extracted(source, model, slots, function_lines)


def patch_source(before: Extracted, after: Extracted, selected) -> str:
    if before.slots.keys() != after.slots.keys():
        raise ValueError('function correspondence differs')
    selected = tuple(selected)
    if len(selected) != len(set(selected)) or any(key not in before.slots for key in selected):
        raise ValueError('unknown or repeated source slot')
    replacements = []
    for key in selected:
        start, end = before.slots[key]
        new_start, new_end = after.slots[key]
        replacements.append((start, end, after.source[new_start:new_end]))
    replacements.sort(reverse=True)
    for index in range(1, len(replacements)):
        if replacements[index][1] > replacements[index - 1][0]:
            raise ValueError('overlapping source slots')
    source = before.source
    for start, end, value in replacements:
        source = source[:start] + value + source[end:]
    extract(source)  # Every emitted hybrid must remain admitted syntax.
    return source


def compiler_warnings(item: Extracted) -> list[dict]:
    """Independent CPython SyntaxWarning observations; no exec/eval or imports."""
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter('always', SyntaxWarning)
        compile(item.source, '<owned-comparison>', 'exec', dont_inherit=True, optimize=0)
    result = []
    for warning in observed:
        if warning.category is not SyntaxWarning or 'is' not in str(warning.message):
            raise ValueError('unexpected compiler diagnostic')
        owners = [name for name, (first, last) in item.function_lines.items()
                  if first <= warning.lineno <= last]
        if len(owners) != 1:
            raise ValueError('compiler warning has no unique admitted owner')
        result.append({'anchor': owners[0], 'line': warning.lineno,
                       'category': warning.category.__name__, 'message': str(warning.message)})
    return result
