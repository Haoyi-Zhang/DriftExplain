"""Evidence reconstruction and change impact at the receiver."""
import json
from pathlib import Path
from diagram_ink import Diagram,S,T,A,K,G,F,L,P,O


def architecture():
    d=Diagram(509,124)
    for y,label,dy in [(91,'Old',20),(41,'New',-20)]:
        d.mark('code',25,y,22,S)
        d.txt(25,y+dy,label,9.8)
        d.wire((37,y),(58,y),(58,66),c=S,arrow=False)
    d.dotmark(58,66,2,c=S,fill=S)
    d.wire((61,66),(88,66),c=S,arrow=False)
    d.dotmark(88,66,2,c=S,fill=S)
    for y,k,label,dy,c in [(91,'graph','Producer',19,S),(41,'array','Checker rebuild',-20,T)]:
        d.wire((90,66),(102,y),(124,y),c=c)
        d.mark(k,141,y,24,c)
        d.txt(141,y+dy,label,10.0,bold=True)
    d.wire((157,91),(219,91),c=S)
    d.mark('cert',236,91,23,S)
    d.txt(236,110,'Certificate',9.6)
    d.wire((247,91),(278,91),(278,51),c=S,dash=True)
    d.wire((157,41),(268,41),c=T)
    d.diamond(278,41,7,T)
    d.txt(238,22,'Claims match?',9.4)
    d.wire((278,32),(278,9),(312,9),c=A,dash=True)
    d.mark('reject',322,9,13,A)
    d.txt(332,9,'Reject',9.3,ha='left',color=A)
    d.wire((287,41),(329,41),c=T,arrow=False)
    d.dotmark(329,41,2,c=T,fill=T)
    for y,k,lab in [(83,'branch','Identify core'),(55,'trace','Verify candidate'),(27,'lens','Check projection')]:
        d.wire((331,41),(358,y),(379,y),c=T)
        d.mark(k,392,y,18,T)
        d.txt(406,y,lab,9.6,ha='left')
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
    for x,t,c in [(42,r'$x=5$',S),(210,r'$x=6$',T)]:
        d.mark('code',x,80,19,c)
        d.txt(x,58,t,10.4,color=c)
    d.wire((58,80),(195,80),c=A)
    d.txt(126,94,'Constant edit',9.1,color=A)
    d.mark('trace',126,60,15,S)
    d.txt(126,43,'Same warning',8.9)
    for x,text,c in [(62,'Value only: 0 atoms',S),(190,'Complete: 1 atom',T)]:
        d.wire((126,35),(126,27),(x,27),(x,20),c=c)
        d.txt(x,9,text,9,color=c)
    return d


def framed_read_closure():
    d=Diagram(252,55)
    d.mark('keyed',20,32,16,S)
    d.txt(29,9,'Decoded prefix',8.65)
    d.wire((31,32),(63,32),c=S)
    d.dotmark(75,32,8,c=S)
    d.node_label(75,32,r'$R_i$',9.3,color=S)
    d.wire((86,32),(103,32),c=S)
    d.node_label(123,32,r'$\bigcup_i\,R_i$',10,color=T)
    d.wire((144,32),(156,32),c=T)
    for x,fill,c,bit in [(164,'white',F,0),(185,P,T,1),(206,'white',F,0),(227,P,T,1)]:
        d.block(x,27,16,10,c,fill)
        if bit:
            d.wire((x+3,34),(x+13,34),c=T,arrow=False,lw=.8)
            d.wire((x+3,30),(x+11,30),c=T,arrow=False,lw=.8)
    d.txt(201,47,'Changed blocks',8.7,color=G)
    d.txt(202,9,'Keep touching edits',8.9,color=T)
    return d


def incremental_impact():
    d=Diagram(252,55)
    for y,label,c in [(43,'Old deps.',S),(12,'New deps.',T)]:
        d.mark('trace',12,y,13,c)
        d.txt(23,y,label,8.7,ha='left',color=c)
        d.wire((71,y),(83,y),(99,28),c=c,arrow=False)
    d.dotmark(99,28,2,c=T,fill=T)
    d.wire((103,28),(122,28),c=T)
    d.mark('patch',131,47,13,S)
    d.node_label(146,47,r'$\Delta$',9.6,color=S)
    d.wire((131,39),(131,36),c=S)
    d.diamond(131,28,6,T)
    d.txt(131,12,'Affected?',8.8)
    for y,k,label,c in [(43,'keyed','Recompute',T),(12,'store','Reuse old',G)]:
        d.wire((139,28),(157,28),(174,y),(184,y),c=c,dash=c==G)
        d.mark(k,195,y,14,c)
        d.txt(205,y,label,8.8,ha='left')
    return d


FIGURES={f.__name__.replace('_','-'):f for f in (
    architecture,literal_evidence,framed_read_closure,incremental_impact)}
