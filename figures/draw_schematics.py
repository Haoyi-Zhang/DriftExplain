"""Render the manuscript schematics as vector PDFs."""
import argparse
from pathlib import Path

def draw(out):
    from validation_panels import drift_architecture as panel
    return panel(out/'architecture.pdf')


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
    out=parser.parse_args().output
    out.mkdir(parents=True,exist_ok=True)
    draw(out)
