import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def render(path):
    data=json.loads((ROOT/'results/source-pairs/summary.json').read_text())
    if data['status']!='PASS' or data['native_model_disagreements']:raise ValueError('incomplete source-pair results')
    fields={'SourcePairInputs':'source_inputs','SourcePairAdmitted':'admitted_pairs','SourcePairExcluded':'excluded_pairs','SourcePairHybrids':'source_realizable_hybrids','SourcePairNative':'native_parse_observations'}
    path.write_text(''.join('\\newcommand{\\'+key+'}{'+str(data[value])+'}\n' for key,value in fields.items()),encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);render(p.parse_args().output)
