#!/usr/bin/env python3
"""Exhaustive bounded validation of the deletion-core theorem.

Enumerates all Boolean predicates on subsets of up to four atoms, retains the
upward-closed predicates accepting the full set, and checks the set-theoretic
claims used by the independent deletion-replay checker. No analyzer code is
imported.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

def subsets(d): return range(1<<d)
def contains(s,t): return (s & t)==t

def upward(mask,d):
    for s in subsets(d):
        if (mask>>s)&1:
            for t in subsets(d):
                if contains(t,s) and not ((mask>>t)&1): return False
    return True

def minimal_sets(sufficient):
    return [s for s in sufficient if not any(t!=s and contains(s,t) for t in sufficient)]

def run(max_atoms=4):
    totals={'dimensions':0,'all_predicates_examined':0,'upward_predicates':0,'theorem_checks':0,'counterexamples':0}
    per=[]; examples=[]
    for d in range(max_atoms+1):
        full=(1<<d)-1; up=0; examined=0
        # predicates are masks over the 2^d subsets
        for pmask in range(1<<(1<<d)):
            examined+=1; totals['all_predicates_examined']+=1
            if not ((pmask>>full)&1): continue
            if not upward(pmask,d): continue
            up+=1; totals['upward_predicates']+=1
            suff=[s for s in subsets(d) if (pmask>>s)&1]
            core=full
            for s in suff: core &= s
            deletion_core=0
            for i in range(d):
                if not ((pmask>>(full & ~(1<<i)))&1): deletion_core |= 1<<i
            mins=minimal_sets(suff)
            principal=all(((pmask>>s)&1)==contains(s,core) for s in subsets(d))
            core_sufficient=bool((pmask>>core)&1)
            unique_least=core_sufficient and all(contains(s,core) for s in suff)
            no_least_implies_multiple=(core_sufficient or len(mins)>=2)
            incomparable=(core_sufficient or all(not contains(a,b) and not contains(b,a) for i,a in enumerate(mins) for b in mins[i+1:]))
            ok=(core==deletion_core and core_sufficient==unique_least==principal and no_least_implies_multiple and incomparable)
            totals['theorem_checks']+=5
            if not ok:
                totals['counterexamples']+=1
                examples.append({'d':d,'predicate_mask':pmask,'sufficient':suff,'core':core,'deletion_core':deletion_core,'minimal':mins,'principal':principal})
                break
        per.append({'atoms':d,'predicates_examined':examined,'upward_full_accepting':up})
        totals['dimensions']+=1
        if examples: break
    # A fixed non-monotone overwrite predicate demonstrates why monotonicity is necessary.
    # sufficient: empty and {a,b}; insufficient: {a}; full accepted.
    nonmonotone={'empty_sufficient':True,'a_sufficient':False,'ab_sufficient':True,'upward_closed':False}
    return {'schema_version':1,'scope':f'all Boolean predicates through {max_atoms} atoms; general theorem still relies on proof','per_dimension':per,'totals':totals,'negative_control':nonmonotone,'status':'PASS' if not examples else 'FAIL','counterexample_examples':examples}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--max-atoms',type=int,default=4);ap.add_argument('--output',type=Path);a=ap.parse_args()
    out=run(a.max_atoms); text=json.dumps(out,indent=2,sort_keys=True)+'\n'
    if a.output:a.output.write_text(text)
    print(text,end='');return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
