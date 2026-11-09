"""Editable manuscript panels."""
import numpy as np
from visual_grammar import *


def drift_delta(out):
    d=Diagram(w=252,h=156)
    labels=['No edit','Only edit 2','Only edit 3','Edits 2 and 3']
    centres=[(59,110),(192,110),(59,47),(192,47)]
    records=[('T','F','F'),('T','T','T'),('U','F','F'),('U','T','U')]
    colors={'T':TEAL,'F':RED,'U':PURPLE}
    for i,(label,(x,y),values) in enumerate(zip(labels,centres,records)):
        if i==3:
            d.rect(x-44,y-18,88,48,GREEN,TEAL,.7)
        d.text(x,y+20,label,9.8,INK,bold=True)
        for j,(state,v) in enumerate(zip(('p','q','rule'),values)):
            xx=x-25+25*j
            d.text(xx,y+5,state,9.1,MUTED)
            d.dot(xx,y-9,5.8,colors[v],'white')
            d.text(xx,y-9,v,8.7,colors[v],bold=True)
    for y in (111,48):
        d.arrow((103,y),(144,y),c=BLUE,lw=.7)
    for x in (59,192):
        d.arrow((x,94),(x,78),c=BLUE,lw=.7)
    d.text(59,16,'T true   F false   U unknown',8.7,MUTED)
    d.text(192,16,'Exact final evidence',8.8,TEAL,bold=True)
    d.finish(out)


def final_read_support(out):
    """Schematic for three disjoint changed coordinates, not a measured case."""
    d=Diagram(w=252,h=95)
    xs=(112,172,226)
    d.text(5,57,'Old reads',9.0,MUTED,'left')
    d.text(5,37,'Final reads',9.0,BLUE,'left',True)
    d.text(5,14,'Least support',9.0,BLUE,'left',True)
    d.line((78,57),(242,57),c=GRID,lw=.55,dash=True)
    d.line((78,37),(242,37),c=GRID,lw=.65)
    for i,(x,label) in enumerate(zip(xs,('Deleted rule','New mapping','Unread edit'))):
        d.text(x,79,label,8.8,INK,bold=i<2)
        d.dot(x,57,2.8,MUTED,MUTED if i==0 else 'white')
        d.dot(x,37,3.1,BLUE if i<2 else MUTED,BLUE if i<2 else 'white')
        if i<2:
            d.arrow((x,31),(x,23),c=BLUE,lw=.63)
            d.text(x,13,'Keep',8.7,BLUE,bold=True)
        else:
            d.text(x,13,'Omit',8.7,MUTED)
    d.finish(out)


def drift_architecture(out):
    d=Diagram(w=508,h=157)
    for x,s in [(66,'Old endpoint'),(170,'New endpoint')]:
        d.doc(x,125)
        d.text(x,144,s,10,BLUE,bold=True)
        d.line((x,114),(x,99),c=BLUE)
    d.line((66,99),(248,99),c=BLUE)
    d.arrow((118,99),(118,72),c=BLUE)
    d.arrow((248,99),(248,72),c=BLUE)
    d.rect(49,37,138,36,WARM,RED,.75,dash=True)
    d.text(118,58,'Untrusted producer',9.5,RED,bold=True)
    d.text(118,45,'Proposed support',8.8)
    d.rect(202,31,100,42,GREEN,TEAL,.75)
    d.text(252,58,'Independent checker',9.5,TEAL,bold=True)
    d.text(252,45,'Rebuilds both endpoints',8.6)
    d.arrow((187,51),(202,51),c=RED,dash=True)
    d.text(162,22,'Certificate',8.7,RED)
    d.line((194,45),(194,22),(185,22),c=RED,dash=True)
    for y,s in [(79,'Identify core'),(51,'Verify candidate'),(23,'Compare projection')]:
        d.arrow((302,51),(334,51),(334,y),(364,y),c=TEAL)
        d.dot(370,y,3,TEAL,'white')
        d.text(381,y,s,9.3,TEAL,'left',True)
    d.finish(out)
