"""Exact subset outcomes for the manuscript's worked interacting delta."""
from diagram_ink import Diagram, S, T, A, G, P

def interaction_support():
    d=Diagram(248,95)
    for x,label in ((48,'Retained edits'),(98,r'$p$'),(122,r'$q$'),
                    (155,r'$p\wedge q$'),(211,'Exact replay')):
        d.txt(x,84,label,9.2,bold=True)
    data=((66,r'$\Delta$','U','T','U',True),
          (52,r'$\{\delta_2,\delta_3\}$','U','T','U',True),
          (38,r'$\{\delta_2\}$','T','T','T',False),
          (24,r'$\{\delta_3\}$','U','F','F',False),
          (10,r'$\varnothing$','T','F','F',False))
    for y,subset,p,q,value,exact in data:
        if y==52:
            d.block(7,y-6,234,12,T,P)
        d.txt(52,y,subset,9.8,color=T if y==52 else G)
        for x,t in ((98,p),(122,q),(155,value)):
            d.txt(x,y,t,9.4,color=T if exact else G)
        d.mark('check' if exact else 'reject',193,y,10,T if exact else A)
        if exact:
            d.txt(203,y,'Redundant' if y==66 else 'Minimal',8.5,
                  ha='left',color=G if y==66 else T)
    return d

FIGURES={'interaction-support':interaction_support}
