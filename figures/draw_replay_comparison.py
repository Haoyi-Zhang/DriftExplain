"""Plot executed call counts from the retained same-input comparison."""
import json
from pathlib import Path
from visual_grammar import Diagram, BLUE, RED, MUTED, GRID


def draw(output, report=None):
    report = report or Path(__file__).resolve().parents[1]/'results/information-paths/report.json'
    data = json.loads(report.read_text(encoding='utf-8'))
    keys = ('identify', 'candidate', 'structure')
    pairs = {(r['d'],r['k']):r['measurements'] for r in data['large_records']}
    assert len(pairs)==len(data['large_records'])==12 and data['decision_disagreements']==0
    assert set(pairs)=={(d,k) for d in (16,32,64) for k in (0,1,d//2,d)}
    for row in pairs.values():
        assert all(row[k]['decision']==[True,'accepted'] and
                   row[k]['delta_reconstructions']==1 and
                   row[k]['evidence_evaluations']==2+row[k]['hybrid_replays'] for k in keys)
    p=Diagram(w=250,h=170)
    xs=(57,110,163,216)
    y=lambda n:41+1.27*n
    for n in (0,16,32,48,64):
        p.line((37,y(n)),(239,y(n)),c=GRID,lw=.65)
        p.text(30,y(n),str(n),9.6,MUTED,'right')
    p.line((37,40),(37,129),c=MUTED)
    p.line((37,41),(239,41),c=MUTED)
    for x,k in zip(xs,(0,1,32,64)):
        p.text(x,30,str(k),9.6)
    p.text(135,14,'Atoms in supplied support',9.8)
    p.text(37,140,'Hybrid replays',9.8,MUTED,'left',True)
    style=(('identify',BLUE,'Identification',22,-13),('candidate',RED,'Replay check',106,0),
           ('structure',MUTED,'Structural check',180,13))
    for key,color,label,lx,offset in style:
        for x,k in zip(xs,(0,1,32,64)):
            count=pairs[64,k][key]['hybrid_replays']
            x+=offset
            if key=='structure':
                assert count==0
                p.cross(x,y(0),color,2.4)
            else:
                p.rect(x-3.8,y(0),7.6,y(count)-y(0),color if key=='identify' else 'white',color,.8)
                dy=8 if key=='identify' else (12 if count>60 else 8)
                p.text(x,y(count)+dy,str(count),9.2,color)
        p.text(lx,158,label,9.1,color,'left')
        if key=='identify':p.rect(lx-9.1,155,4.2,4,color,color,.85)
        elif key=='candidate':p.rect(lx-9.1,155,4.2,4,'white',color,.85)
        else:p.cross(lx-6,157,color,2.4)
    p.finish(output)


if __name__ == '__main__':
    draw(Path(__file__).with_name('replay-comparison.pdf'))
