"""Exact subset outcomes for the manuscript's worked interacting delta."""
from diagram_ink import Diagram, S, T, A

def interaction_support():
    d=Diagram(248,95)
    d.wire((39,49),(95,49),c=T)
    d.wire((136,56),(154,75),c=S)
    d.wire((136,43),(154,28),c=S)
    d.wire((188,75),(216,55),c=S)
    d.wire((188,28),(216,43),c=S)
    d.txt(66,59,r'drop $\delta_1$',8.8,color=T)
    nodes=((23,49,r'$\Delta$','U',True),
           (115,49,r'$\{\delta_2,\delta_3\}$','U',True),
           (172,78,r'$\{\delta_2\}$','T',False),
           (172,27,r'$\{\delta_3\}$','F',False),
           (230,49,r'$\varnothing$','F',False))
    for x,y,subset,value,exact in nodes:
        c=T if exact else S
        d.txt(x,y,subset,10.0,color=c)
        d.txt(x-3,y-13,value,9.0,color=c)
        d.mark('check' if exact else 'reject',x+7,y-13,8,c if exact else A)
    return d

FIGURES={'interaction-support':interaction_support}
