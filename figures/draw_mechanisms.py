"""Rebuild the paper's mechanism schematics at their intended physical size."""
from pathlib import Path
from diagram_core import Figure, BLUE, GRAY, INK, RED

def impact_union(f):
    f.node(53,19,'trace','Old reads')
    f.node(53,67,'trace','New reads')
    f.route((80,19),(121,19),(121,43),(165,43))
    f.route((80,67),(121,67),(121,49),(165,49))
    f.node(190,46,'merge','Union impact')
    f.route((214,46),(245,46),(245,19),(276,19))
    f.route((245,46),(245,68),(276,68),dash=True,color=GRAY)
    f.node(303,19,'run','Recompute',side='right')
    f.node(303,68,'store','Reuse',side='right',color=GRAY)
    f.t(345,88,'outside impact',color=GRAY)

FIGURES = [('impact_union', 244, 92)]

if __name__ == '__main__':
    for name,w,h in FIGURES:
        f=Figure(dict(media=(w,h),trim=(0,0,0,0),width=w))
        globals()[name](f)
        f.finish(Path(__file__).parent/(name.replace('_','-')+'.pdf'))
