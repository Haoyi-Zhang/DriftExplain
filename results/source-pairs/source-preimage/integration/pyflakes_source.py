"""Automatic whole-module export of one released Pyflakes diagnostic family.

This is a source frontend, not a generic export of all Pyflakes internals.
Comparison-chain edges are exported individually, including IsNot, literals
on either side and nested tuple constants. Location anchors refer to the same
source: this module does not infer correspondence across changed files.
"""
from __future__ import annotations
import ast
import hashlib


def export_source(source, release):
    if release not in ('2.1.1','2.2.0') or type(source) is not str:
        raise ValueError('source/release contract')
    if len(source.encode('utf-8')) > 65536:
        raise ValueError('source byte bound')
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    if len(nodes) > 10000: raise ValueError('syntax node bound')
    # These releases can parse extra annotations as separate source. Such
    # evidence is not a direct comparison node of this source AST.
    if any(isinstance(n, ast.AnnAssign) or
           isinstance(n, (ast.FunctionDef,ast.AsyncFunctionDef)) and n.returns is not None or
           isinstance(n, ast.arg) and n.annotation is not None or
           isinstance(n, ast.ImportFrom) and n.module == '__future__' or
           type(n).__name__ in {'NamedExpr','Match','TryStar','TypeAlias'} for n in nodes):
        raise ValueError('annotation/deferred/newer-syntax profile is unsupported')
    def scalar(n):
        return type(n) is ast.Constant and type(n.value) in (str,bytes,int,float,complex)
    def constant(n):
        return type(n) is ast.Constant or type(n) is ast.Tuple and all(constant(x) for x in n.elts)
    def tuple_literal(n):
        return type(n) is ast.Tuple and constant(n)
    targets, locations = [], []
    for node in sorted((n for n in nodes if type(n) is ast.Compare),
                       key=lambda n:(n.lineno,n.col_offset)):
        left = node.left
        for pair,(op,right) in enumerate(zip(node.ops,node.comparators)):
            if len(targets) >= 200: raise ValueError('comparison edge bound')
            anchor = f'L{node.lineno}C{node.col_offset}P{pair}'
            a,b = ast.dump(left,include_attributes=False),ast.dump(right,include_attributes=False)
            targets.append(dict(anchor=anchor,
                raw=dict(identity='T' if type(op) in (ast.Is,ast.IsNot) else 'F',
                         scalar='T' if scalar(left) or scalar(right) else 'F',
                         tuple='T' if tuple_literal(left) or tuple_literal(right) else 'F'),
                origins=dict(identity=ast.dump(op),scalar=a+' / '+b,tuple=a+' / '+b)))
            locations.append(dict(anchor=anchor,line=node.lineno,column=node.col_offset,pair=pair))
            left = right
    model = dict(targets=targets,normalizer=dict(identity=['identity'],
        literal=['scalar','tuple'] if release=='2.2.0' else ['scalar']),
        rules=[dict(id='IsLiteral',family='IsLiteral',requires=['identity','literal'],forbids=[])])
    return dict(model=model,locations=locations,source_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
        profile='direct-source comparison family, no annotations/doctests or changed-file anchor matching')


def make_source_certificate(source, old_release, new_release, anchor):
    """Producer entry: emit a packet for an explicit source and two policies."""
    import producer
    old,new=(export_source(source,v) for v in (old_release,new_release))
    return dict(binding=dict(source_sha256=old['source_sha256'],
        old_release=old_release,new_release=new_release),
        certificate=producer.make_certificate(old['model'],new['model'],'IsLiteral',anchor))


def check_source_certificate(source, old_release, new_release, packet):
    """Receiver entry: reconstruct expected models from separate source bytes."""
    import checker
    old,new=(export_source(source,v) for v in (old_release,new_release))
    expected=dict(source_sha256=old['source_sha256'],old_release=old_release,new_release=new_release)
    if type(packet) is not dict or set(packet)!={'binding','certificate'} or packet['binding']!=expected:
        return False,'source or release binding mismatch'
    return checker.check_certificate(old['model'],new['model'],packet['certificate'])
