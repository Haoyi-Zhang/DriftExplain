"""Fail-closed source bridge for an owned Python identity-comparison fragment.

Only parse/compile source; never execute it. This is not a general Python or
Solidity analyzer. Stable function names identify one comparison each. Operator
and operand syntax are independently editable observation slots.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import io
import re
import tokenize
import warnings


@dataclass(frozen=True)
class Extracted:
    source: str
    model: dict
    slots: dict
    function_lines: dict


class _SourceCoordinates:
    """Translate physical lines and AST UTF-8 byte columns to string offsets.

    Unlike str.splitlines(), Python's physical lines do not end at form feeds
    or other control characters embedded in whitespace/comments. AST columns
    count UTF-8 bytes, whereas tokenize columns and string slices count chars.
    The public bridge still admits ASCII only; keeping these units explicit
    avoids silently weakening that contract if coordinates are reused.
    """
    def __init__(self, source: str):
        self.lines, self.starts = [], []
        start = 0
        for ending in re.finditer(r'\r\n|\r|\n', source):
            self.starts.append(start)
            self.lines.append(source[start:ending.start()])
            start = ending.end()
        self.starts.append(start)
        self.lines.append(source[start:])

    def token_offset(self, row: int, column: int) -> int:
        if not 1 <= row <= len(self.lines) or not 0 <= column <= len(self.lines[row - 1]):
            raise ValueError('source coordinate outside physical line')
        return self.starts[row - 1] + column

    def ast_offset(self, row: int, byte_column: int) -> int:
        if not 1 <= row <= len(self.lines):
            raise ValueError('AST coordinate outside physical lines')
        encoded = self.lines[row - 1].encode('utf-8')
        if not 0 <= byte_column <= len(encoded):
            raise ValueError('AST byte column outside physical line')
        try:
            column = len(encoded[:byte_column].decode('utf-8'))
        except UnicodeDecodeError as error:
            raise ValueError('AST byte column splits a UTF-8 character') from error
        return self.token_offset(row, column)


def extract(source: str) -> Extracted:
    if type(source) is not str or not source.isascii() or len(source) > 8192:
        raise ValueError('source must be bounded ASCII text')
    tree = ast.parse(source)
    coordinates = _SourceCoordinates(source)
    # tokenize.readline expects LF boundaries; retain original offsets for
    # slicing CRLF/CR source and normalize only this lexical view.
    lexical_source = source.replace('\r\n', '\n').replace('\r', '\n')
    tokens = tuple(tokenize.generate_tokens(io.StringIO(lexical_source).readline))
    if not 1 <= len(tree.body) <= 8:
        raise ValueError('expected one to eight functions')
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
        left_end = coordinates.ast_offset(compare.left.end_lineno, compare.left.end_col_offset)
        right_start = coordinates.ast_offset(right.lineno, right.col_offset)
        # AST operand offsets do not delimit the operator: the intervening
        # text can include the closing parentheses of the left operand and
        # opening parentheses of the right one. Splicing that whole region
        # can create an unmatched delimiter in an otherwise admitted hybrid.
        operator = 'is' if type(compare.ops[0]) is ast.Is else '=='
        operators = [token for token in tokens
                     if token.string == operator and token.start[0] == compare.lineno
                     and coordinates.token_offset(*token.start) >= left_end
                     and coordinates.token_offset(*token.end) <= right_start]
        if len(operators) != 1:
            raise ValueError('comparison operator has no unique lexical span')
        token = operators[0]
        slots['program|' + anchor + '|identity'] = (
            coordinates.token_offset(*token.start), coordinates.token_offset(*token.end))
        slots['program|' + anchor + '|constant'] = (
            right_start, coordinates.ast_offset(right.end_lineno, right.end_col_offset))
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
        replacement = after.source[new_start:new_end]
        # In compact x==x syntax a keyword replacement must not become xisx.
        # Padding touches no operand or extracted descriptor.
        if key.endswith('|identity'):
            replacement = ' ' + replacement + ' '
        replacements.append((start, end, replacement))
    replacements.sort(reverse=True)
    for index in range(1, len(replacements)):
        if replacements[index][1] > replacements[index - 1][0]:
            raise ValueError('overlapping source slots')
    source = before.source
    for start, end, value in replacements:
        source = source[:start] + value + source[end:]
    # Syntax admission alone cannot detect a valid splice into the wrong span.
    # Check the actual extraction/finite-patch commuting square on every output.
    from producer import apply_operations, compute_delta
    operations = [operation for operation in compute_delta(before.model, after.model)
                  if operation['id'] in selected]
    expected = apply_operations(before.model, operations)
    if extract(source).model != expected:
        raise ValueError('source extraction and finite patch disagree')
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
