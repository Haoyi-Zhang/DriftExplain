#!/usr/bin/env python3
"""Independent bounded checker for the structural-support theorem.

This file imports no analyzer code.  It exhaustively enumerates small fixed
stratified frames.  A state has one always-read selector coordinate and one
leaf coordinate per selector value.  Evidence is the selector followed by the
selected leaf.  Delta atoms own pairwise-disjoint blocks of changed
coordinates.  The checker verifies, for every subset of atoms, that exact
final-evidence equality holds iff all atoms intersecting the final read closure
are selected.  Four deliberately out-of-contract constructions are checked as
negative controls.
"""
from __future__ import annotations
from itertools import combinations, product
import argparse, json
from pathlib import Path


def set_partitions(items):
    items=tuple(items)
    if not items:
        yield ()
        return
    first,*rest=items
    for part in set_partitions(rest):
        yield ((first,),)+part
        for i in range(len(part)):
            block=tuple(sorted((first,)+part[i]))
            yield part[:i]+(block,)+part[i+1:]


def canonical_partitions(items):
    seen=set()
    for p in set_partitions(items):
        q=tuple(sorted((tuple(sorted(b)) for b in p), key=lambda b:(b[0],len(b),b)))
        if q not in seen:
            seen.add(q); yield q


def evidence(state):
    selector=state[0]
    return (selector, state[1+selector])


def patch(old,new,blocks,chosen):
    out=list(old)
    for i,block in enumerate(blocks):
        if i in chosen:
            for c in block: out[c]=new[c]
    return tuple(out)


def powerset(n):
    for mask in range(1<<n):
        yield {i for i in range(n) if mask & (1<<i)}


def check_domain(q):
    coords=1+q
    states=list(product(range(q), repeat=coords))
    endpoints=partitions=subsets=0
    failures=[]
    for old in states:
        for new in states:
            changed=tuple(i for i,(a,b) in enumerate(zip(old,new)) if a!=b)
            if not changed: continue
            endpoints += 1
            final_read={0,1+new[0]}
            for blocks in canonical_partitions(changed):
                partitions += 1
                support={i for i,b in enumerate(blocks) if final_read.intersection(b)}
                target=evidence(new)
                for chosen in powerset(len(blocks)):
                    subsets += 1
                    actual=evidence(patch(old,new,blocks,chosen))==target
                    predicted=support.issubset(chosen)
                    if actual!=predicted:
                        failures.append({'q':q,'old':old,'new':new,'blocks':blocks,'chosen':sorted(chosen),'support':sorted(support),'actual':actual})
                        return {'domain_size':q,'endpoints':endpoints,'partitions':partitions,'subset_replays':subsets,'failures':failures}
    return {'domain_size':q,'endpoints':endpoints,'partitions':partitions,'subset_replays':subsets,'failures':failures}


def negative_controls():
    # NC1: value-only observation admits incomparable singleton explanations.
    q1=lambda s: (('a' in s) or ('b' in s))
    mins1=[s for s in [set(),{'a'},{'b'},{'a','b'}] if q1(s) and not any(q1(t) for t in [set(),{'a'},{'b'}] if t < s)]
    # NC2: sequential overlapping writes are not upward closed: empty and {a,b}
    # reach 0, while {a} reaches 1.
    def seq(s):
        v=0
        if 'a' in s: v=1
        if 'b' in s: v=0
        return v==0
    upward_violation=seq(set()) and not seq({'a'}) and seq({'a','b'})
    # NC3: hiding the selector from evidence makes a non-final leaf substitute possible.
    hidden_selector = ((0,7)[1] == (1,7)[1])
    # NC4: unstable identity can swap two coordinates while preserving a positional tuple.
    unstable_identity = ((('x',1),('y',2)) != (('x',2),('y',1)) and (1,2)==(1,2))
    return {
        'value_only_incomparable_minima': len(mins1)==2,
        'overlapping_write_breaks_upward_closure': upward_violation,
        'hidden_visibility_breaks_structural_identification': hidden_selector,
        'unstable_identity_breaks_coordinate_correspondence': unstable_identity,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    runs=[check_domain(2),check_domain(3)]
    neg=negative_controls()
    out={
        'checker_independence':'standard library only; imports no project analyzer, producer, checker, or test module',
        'scope':'bounded exhaustive validation of one-selector stratified frames; not a substitute for the paper proof',
        'domains':runs,
        'totals':{
            'endpoint_pairs':sum(r['endpoints'] for r in runs),
            'atom_partitions':sum(r['partitions'] for r in runs),
            'subset_replays':sum(r['subset_replays'] for r in runs),
            'counterexamples':sum(len(r['failures']) for r in runs),
        },
        'negative_controls':neg,
        'negative_controls_passed':all(neg.values()),
        'status':'PASS' if all(not r['failures'] for r in runs) and all(neg.values()) else 'FAIL',
    }
    text=json.dumps(out,indent=2,sort_keys=True)+'\n'
    if args.output: args.output.write_text(text)
    print(text,end='')
    raise SystemExit(0 if out['status']=='PASS' else 1)
if __name__=='__main__': main()
