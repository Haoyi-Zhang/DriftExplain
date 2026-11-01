"""Source-realizable, block-addressed correspondence for one diagnostic family.

The full enclosing AST must match after replacing every comparison expression
by a hole. Single-edge, nonnested comparisons are whole source atoms; internal
scalar/tuple/operator observations are not independently editable source atoms.
Whitespace and line displacement are irrelevant to AST paths. Other structural
changes, chains, nested comparisons or ambiguous correspondence fail closed.
Input programs are parsed, never imported or executed.
"""
from __future__ import annotations
import ast
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from itertools import combinations
from pyflakes_source import export_source

MAX_COMPARISONS=8
MAX_BLOCKS=9

def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

@dataclass
class SourceFrame:
    source:str
    frame:str
    slots:dict
    model:dict
    locations:dict

def extract(source,release):
    if type(source) is not str or not source.isascii():raise ValueError('bounded ASCII source required')
    exported=export_source(source,release)
    tree=ast.parse(source);slots={};coordinates={}
    lines=source.splitlines(keepends=True);offsets=[0]
    for line in lines:offsets.append(offsets[-1]+len(line))
    def walk(node,path):
        if type(node) is ast.Compare:
            if len(node.ops)!=1 or any(type(c) is ast.Compare for child in ast.iter_child_nodes(node) for c in ast.walk(child)):
                raise ValueError('chains and nested comparisons have no disjoint whole-edge slots')
            if len(slots)>=MAX_COMPARISONS:raise ValueError('comparison bound')
            key='ast/'+path
            slots[key]=(offsets[node.lineno-1]+node.col_offset,offsets[node.end_lineno-1]+node.end_col_offset)
            coordinates[(node.lineno,node.col_offset,0)]=key
            return ast.Constant(value='comparison-hole')
        replacement=deepcopy(node)
        for field,value in ast.iter_fields(node):
            if isinstance(value,ast.AST):setattr(replacement,field,walk(value,path+'/'+field))
            elif isinstance(value,list):setattr(replacement,field,[walk(x,path+'/'+field+'/'+str(i)) if isinstance(x,ast.AST) else x for i,x in enumerate(value)])
        return replacement
    frame=ast.dump(walk(tree,'module'),include_attributes=False)
    if len(slots)!=len(exported['locations']):raise ValueError('incomplete comparison coverage')
    by={loc['anchor']:coordinates[(loc['line'],loc['column'],loc['pair'])] for loc in exported['locations']}
    model=deepcopy(exported['model']);locations={}
    for loc in exported['locations']:locations[by[loc['anchor']]]=dict(loc)
    for row in model['targets']:row['anchor']=by[row['anchor']]
    model['targets'].sort(key=lambda row:row['anchor'])
    return SourceFrame(source,frame,slots,model,locations)

class SourcePair:
    def __init__(self,before,after,old_release,new_release):
        self.before=extract(before,old_release);self.after=extract(after,new_release)
        self.old_release,self.new_release=old_release,new_release
        if self.before.frame!=self.after.frame or self.before.slots.keys()!=self.after.slots.keys():
            raise ValueError('enclosing AST or comparison correspondence changed')
        import producer
        self.delta=producer.compute_delta(self.before.model,self.after.model)
        blocks={}
        for op in self.delta:
            if op['kind']=='program':key='source:'+op['anchor']
            elif op['kind']=='normalizer' and op['canonical']=='literal':key='policy:literal'
            else:raise ValueError('unaccounted model change')
            blocks.setdefault(key,[]).append(op['id'])
        if len(blocks)>MAX_BLOCKS:raise ValueError('source/policy block bound')
        self.blocks={key:sorted(value) for key,value in sorted(blocks.items())}
        # Coordinate splices must have pairwise disjoint byte spans.
        spans=sorted(self.before.slots.values())
        if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('overlapping comparison spans')
        # At most nine source/policy blocks: establish total realizability at
        # admission, not only when a later caller happens to request a hybrid.
        keys=tuple(self.blocks)
        for size in range(len(keys)+1):
            for selected in combinations(keys,size):self.hybrid(selected)

    def hybrid(self,selected):
        selected=tuple(selected)
        if len(selected)!=len(set(selected)) or any(k not in self.blocks for k in selected):raise ValueError('unknown or repeated block')
        replacements=[]
        for key in selected:
            if key.startswith('source:'):
                anchor=key[len('source:'):];a,b=self.before.slots[anchor];c,d=self.after.slots[anchor]
                replacements.append((a,b,self.after.source[c:d]))
        release=self.new_release if 'policy:literal' in selected else self.old_release
        import producer
        ids={v for key in selected for v in self.blocks[key]}
        expected=producer.apply_operations(self.before.model,[op for op in self.delta if op['id'] in ids])
        # Keep historical valid splices byte-identical. If raw AST spans lose
        # enclosing parentheses or continuation context, retry wrapped operands.
        for wrapped in (False,True):
            source=self.before.source
            for a,b,value in sorted(replacements,reverse=True):
                source=source[:a]+('('+value+')' if wrapped else value)+source[b:]
            try:
                result=extract(source,release)
                if result.frame!=self.before.frame:raise ValueError('hybrid left the fixed AST frame')
                if result.model!=expected:raise ValueError('source realization and model hybrid disagree')
                return source,release,result
            except (SyntaxError,ValueError):
                if wrapped:raise

    def support(self,anchor):
        import producer
        packet=producer.make_certificate(self.before.model,self.after.model,'IsLiteral',anchor,maximum_changes=64)
        fields=set(packet['witness'])
        blocks=[key for key,ids in self.blocks.items() if fields.intersection(ids)]
        return blocks,packet

    def binding(self):
        return dict(before=digest(self.before.source),after=digest(self.after.source),
            old_release=self.old_release,new_release=self.new_release,frame=digest(self.before.frame),blocks=self.blocks)

def make_pair_certificate(before,after,old_release,new_release,anchor):
    pair=SourcePair(before,after,old_release,new_release)
    blocks,packet=pair.support(anchor)
    return dict(binding=pair.binding(),source_support=blocks,certificate=packet)

def check_pair_certificate(before,after,old_release,new_release,packet):
    import checker
    try:
        pair=SourcePair(before,after,old_release,new_release)
        if type(packet) is not dict or set(packet)!={'binding','source_support','certificate'}:return False,'packet fields'
        if packet['binding']!=pair.binding():return False,'source/frame binding'
        cert=packet['certificate']
        ok,reason=checker.check_certificate(pair.before.model,pair.after.model,cert,maximum_changes=64)
        if not ok:return False,reason
        expected=[key for key,ids in pair.blocks.items() if set(cert['witness']).intersection(ids)]
        if packet['source_support']!=expected:return False,'source block projection'
        return True,'accepted source-realizable block support'
    except (KeyError,TypeError,ValueError,SyntaxError) as exc:
        return False,str(exc)
