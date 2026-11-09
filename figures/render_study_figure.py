"""Render the manuscript example as a vector PDF."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "artifact/figures"))

def drift(output):
    from validation_panels import drift_delta as panel
    return panel(output)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path(__file__).with_name('interacting-delta.pdf'))
    p.add_argument('--support-output',type=Path,default=Path(__file__).with_name('final-read-support.pdf'))
    a=p.parse_args()
    drift(a.output)
    from validation_panels import final_read_support
    final_read_support(a.support_output)
