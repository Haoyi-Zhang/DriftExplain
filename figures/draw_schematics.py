"""Draw publication figures from the retained endpoint and replay records."""
import argparse
import csv
import json
from pathlib import Path
from pictograms import icon
from figure_style import AMBER, BLUE, LIGHT, TEAL, Plate, grid, paper_style, plot, save

ROOT = Path(__file__).resolve().parents[1]


def draw(out):
    from diagram_ink import emit
    emit('architecture',out)

def literal_evidence(out):
    from diagram_ink import emit
    emit('literal-evidence',out)

def replay_counts(out):
    with (ROOT/'results/candidate_verification/finite_query_counts.csv').open(
            encoding='utf-8',newline='') as f:
        data=[r for r in csv.DictReader(f) if int(r['delta_atoms'])==64]
    assert [int(r['support_atoms']) for r in data]==[0,1,32,64]
    assert all(r['both_accept']=='True' for r in data)
    identify={int(r['identification_checker_hybrid_replays']) for r in data}
    verify=[int(r['candidate_verifier_hybrid_replays']) for r in data]
    assert identify=={65} and verify==[1,2,33,64]
    fig,ax=plot(252,121,left=54,right=15,bottom=30,top=24)
    y=list(range(len(data)))
    ax.axvline(identify.pop(),color=AMBER,linestyle='--',linewidth=.8,label='Identify core (65)')
    ax.scatter(verify,y,marker='o',s=11,facecolors='white',edgecolors=BLUE,
               linewidths=.7,label='Verify candidate',zorder=4)
    for value,row in zip(verify,y):
        dx = -5 if value == 64 else 5
        ax.annotate(str(value),(value,row),xytext=(dx,0),textcoords='offset points',
                    ha='right' if dx<0 else 'left',va='center',fontsize=8.8,color=BLUE)
    ax.set(xlim=(-3,72),ylim=(3.45,-.45),xticks=[0,16,32,48,64],
           yticks=y,yticklabels=[f"{r['support_atoms']} atom" + ('s' if r['support_atoms'] != '1' else '') for r in data],
           xlabel='Hybrid replays')
    # The four rows are selected cases, not a quantitative vertical axis.
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y',length=0,pad=4)
    ax.legend(loc='lower left',bbox_to_anchor=(-.21,1.02),ncol=2,fontsize=8.6,
              handlelength=1.55,handletextpad=.5,columnspacing=.9)
    grid(ax,'x')
    save(fig,out,'replay-counts')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    paper_style('tpds')
    out=parser.parse_args().output
    draw(out)
    literal_evidence(out)
    replay_counts(out)
    from diagram_ink import emit_supplemental
    emit_supplemental(out)
