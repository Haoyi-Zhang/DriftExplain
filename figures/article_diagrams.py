"""Evidence reconstruction and change impact at the receiver."""
import json
from pathlib import Path
from diagram_ink import Diagram,S,T,A,K,G,F,L,P,O
from matplotlib.patches import FancyBboxPatch


def architecture():
    d=Diagram(509,132)
    d.tag(13,117,'One changed operand')
    d.tag(172,117,'Two observation contracts')
    d.tag(380,117,'Witness check')
    for y,n,c in ((87,5,S),(52,6,A)):
        d.mark('code',25,y,17,c)
        d.txt(46,y,f'return x is {n}',9.8,ha='left',color=c)
        d.wire((115,y),(145,y),c=c)
        d.dotmark(155,y,2,c=c,fill=c)
        d.wire((158,y),(175,y),c=c,arrow=False)
        d.mark('trace',185,y,13,G)
        d.txt(197,y,'Warning',9.0,ha='left')
        d.dotmark(250,y,7,c=c)
        d.node_label(250,y,str(n),10.3,color=c)
    d.wire((237,84),(233,84),(233,55),(237,55),c=G,arrow=False)
    d.txt(211,25,'Same warning',9.1,color=G)
    d.wire((249,78),(249,61),c=A,dash=True)
    d.wire((260,69),(293,69),c=A)
    d.dotmark(306,69,7,c=A)
    d.node_label(306,69,r'$\delta$',10,color=A)
    d.wire((316,69),(343,69),(343,82),(364,82),c=T)
    for y,label,c in ((82,r'Recovered $\{\delta\}$',T),(52,r'Submitted $W$',G)):
        d.ax.add_patch(FancyBboxPatch((366,y-8),92,16,boxstyle='round,pad=0,rounding_size=3',
                      linewidth=.72,edgecolor=c,facecolor='white',zorder=3))
        d.node_label(412,y,label,9.4,color=c)
        d.wire((461,y),(479,67),c=c,arrow=False)
    d.dotmark(487,67,7,c=T)
    d.node_label(487,67,'=',9.5,color=T)
    d.txt(477,32,'Must agree',8.7,color=T)
    return d


def literal_evidence():
    report=json.loads((Path(__file__).resolve().parents[1]/
                       'results/source-bridge/report.json').read_text(encoding='utf-8'))
    case=next(p for p in report['packets'] if p['name']=='warning-preserved-literal-cause-changed')
    focus=next(p for p in case['candidates'] if p['anchor']=='focus')
    edit,=case['delta']
    assert (edit['anchor'],edit['raw'])==('focus','constant')
    assert [edit[v]['origin'] for v in ('old','new')]==['Constant(value=5)','Constant(value=6)']
    assert all([w['anchor'] for w in h['compiler_warnings']]==['focus'] for h in case['hybrids'])
    assert focus['minimum_value_support']==0 and focus['certificate']['witness']==[edit['id']]
    d=Diagram(252,107)
    d.txt(12,94,'Edit set',8.9,ha='left',bold=True)
    d.txt(102,94,'Line 2',8.9,bold=True)
    d.txt(187,94,'Matches target',8.9,bold=True)
    for x,label in [(165,'Warning'),(221,'Literal')]:
        d.txt(x,77,label,8.6)
    for y,lab,lit,tone in [(57,r'$\varnothing$','5',S),(29,r'$\{\delta\}$','6',T)]:
        d.txt(31,y,lab,9.7,color=tone)
        d.mark('code',77,y,11,tone)
        d.txt(111,y,'x is '+lit,9.0,color=tone)
        d.mark('check' if lit=='6' else 'reject',221,y,11,T if lit=='6' else A)
    d.wire((147,60),(153,60),(153,26),(147,26),c=G,arrow=False)
    d.mark('check',165,43,11,T)
    d.txt(9,9,r'$\delta$: literal edit',8.5,ha='left')
    d.txt(242,9,'Target operand: 6',8.5,ha='right',color=G)
    return d


def framed_read_closure():
    d=Diagram(252,62)
    d.txt(6,50,'Reads',8.4,ha='left',bold=True)
    d.txt(6,25,'Edits',8.4,ha='left',bold=True)
    d.txt(62,50,'Unread',7.8,color=G)
    for x,key,edit,c in ((62,'a',1,G),(97,'b',2,T),(128,'c',3,T)):
        if key!='a':
            d.dotmark(x,50,6,c=c,fill=P)
            d.node_label(x,50,rf'${key}$',9.1,color=c)
            d.wire((x,42),(x,33),c=T,dash=True)
        d.block(x-10,18,20,14,c,'white')
        d.node_label(x,25,rf'$\delta_{edit}$',9.0,color=c)
    d.wire((105,50),(120,50),c=S)
    d.wire((97,17),(97,7),(149,7),(149,25),(156,25),c=T)
    d.wire((128,17),(128,7),c=T,arrow=False)
    d.dotmark(128,7,1.3,c=T,fill=T)
    d.txt(174,39,'Support',8.4,bold=True)
    d.block(157,18,35,14,T,P)
    d.node_label(174.5,25,r'$\{\delta_2,\delta_3\}$',8.6,color=T)
    d.wire((193,25),(198,25),c=T)
    d.diamond(204,25,5,c=G)
    d.txt(204,51,r'$W$',9.1,color=G)
    d.wire((204,43),(204,31),c=G)
    d.wire((210,26),(218,34),c=T)
    d.wire((210,24),(218,14),c=A,dash=True)
    d.txt(250,36,'Accept',8.4,ha='right',color=T)
    d.txt(250,12,'Reject',8.4,ha='right',color=A)
    d.txt(216,42,r'$=$',8.5,color=T)
    d.txt(208,9,r'$\ne$',8.5,color=A)
    return d


def incremental_impact():
    d=Diagram(252,101)
    d.tag(12,90,r'Reads changed key $k$')
    d.tag(137,90,'Cache action')
    d.txt(53,73,'Old',8.8)
    d.txt(88,73,'New',8.8)
    for y,n,old,new in ((55,'u',True,False),(37,'v',False,True),(19,'w',False,False)):
        d.dotmark(21,y,6.4,c=S if old or new else G)
        d.node_label(21,y,n,9.4)
        for x,active in ((53,old),(88,new)):
            if active:
                d.mark('check',x,y,10,S)
            else:
                d.txt(x,y,r'$-$',8.7,color=G)
    d.wire((103,55),(113,55),(124,46),c=T,arrow=False)
    d.wire((103,37),(113,37),(124,46),c=T,arrow=False)
    d.dotmark(124,46,1.65,c=T,fill=T)
    d.wire((127,46),(138,46),c=T)
    d.txt(146,46,'Recompute at new endpoint',8.5,ha='left',color=T)
    d.wire((103,19),(138,19),c=G,dash=True)
    d.txt(146,22,'Reuse if cache is correct',8.5,ha='left',color=G)
    d.txt(146,10,'and no other key affects it',8.5,ha='left',color=G)
    return d


FIGURES={f.__name__.replace('_','-'):f for f in (
    architecture,literal_evidence,framed_read_closure,incremental_impact)}
