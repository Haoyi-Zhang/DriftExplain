"""Evidence reconstruction and change impact at the receiver."""
import json
from pathlib import Path
from diagram_ink import Diagram,S,T,A,K,G,F,L,P,O


def architecture():
    d=Diagram(509,124)
    d.mark('code',18,89,19,S);d.txt(33,89,'Original inputs',9.6,ha='left')
    d.mark('cert',18,37,21,A);d.txt(33,37,'Certificate',9.6,ha='left')
    d.zone(128,12,295,94,fill='white')
    d.tag(137,115,'Independent checker')
    d.wire((99,89),(147,89),c=S)
    d.txt(153,89,'Reconstruct endpoints and delta',9.4,ha='left')
    d.wire((292,89),(322,89),(322,66),c=S)
    d.wire((82,37),(268,37),(268,58),(312,58),c=A,dash=True)
    d.txt(163,46,'Claimed support',8.9,color=A)
    d.diamond(322,58,7.5,T)
    d.txt(341,58,'Check support',9.4,ha='left')
    d.wire((401,58),(457,58),c=T)
    d.txt(465,58,'Verdict',9.8,ha='left',color=T)
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
    d.mark('code',42,79,22,S);d.mark('code',210,79,22,T)
    d.txt(42,57,'x is 5',9.4);d.txt(210,57,'x is 6',9.4)
    d.wire((57,79),(195,79),c=A)
    d.txt(126,93,'Constant edit',8.9,color=A)
    d.txt(126,62,'Same warning',9.0)
    d.wire((126,53),(126,38),(65,38),(65,29),c=S)
    d.wire((126,38),(187,38),(187,29),c=T)
    d.txt(65,15,'Value only: 0 atoms',8.8,color=S)
    d.txt(187,15,'Complete: 1 atom',8.8,color=T)
    return d


def framed_read_closure():
    d=Diagram(252,55)
    d.mark('keyed',38,36,18,S)
    d.txt(38,18,'Decoded prefix',8.7,color=S)
    d.wire((54,36),(98,36),c=S)
    d.txt(119,36,r'$R_i(n)$',10.1,color=T)
    d.txt(119,18,'Next visible keys',8.7,color=T)
    d.wire((141,36),(169,36),c=T)
    d.txt(202,36,r'$\bigcup_i R_i(n)$',10.1,color=T)
    d.wire((202,28),(202,20),c=T)
    d.txt(198,10,'Keep intersecting edits',8.8,color=T)
    return d


def incremental_impact():
    d=Diagram(252,55)
    d.txt(9,43,'Old reads',8.5,ha='left',color=S)
    d.txt(9,15,'New reads',8.5,ha='left',color=T)
    d.wire((54,43),(83,43),(83,29),(102,29),c=S)
    d.wire((54,15),(83,15),(83,29),c=T,arrow=False)
    d.dotmark(111,29,6,c=T);d.txt(111,29,r'$\cup$',8.8,color=T)
    d.wire((118,29),(142,29),(142,43),(170,43),c=T)
    d.wire((142,29),(142,15),(170,15),c=G,dash=True)
    d.txt(181,43,'Recompute impact',8.3,ha='left')
    d.txt(181,15,'Reuse elsewhere',8.3,ha='left')
    return d


FIGURES={f.__name__.replace('_','-'):f for f in (
    architecture,literal_evidence,framed_read_closure,incremental_impact)}
