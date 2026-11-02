import argparse
from pathlib import Path
if __package__:
    from .check_source_pairs import verify
else:
    from check_source_pairs import verify


def render(path):
    # Reconstruct and validate the retained evidence before opening any output.
    # Use the verified counts, not a second independent read of the summary.
    data=verify()
    fields={'SourcePairInputs':'source_inputs','SourcePairAdmitted':'admitted_pairs','SourcePairExcluded':'excluded_pairs','SourcePairHybrids':'source_realizable_hybrids','SourcePairNative':'native_parse_observations'}
    content=''.join('\\newcommand{\\'+key+'}{'+str(data[value])+'}\n' for key,value in fields.items())
    # Exclusive creation also protects an existing paper or retained output on
    # valid input, including a destination created after validation started.
    with path.open('x',encoding='utf-8',newline='\n') as output:
        output.write(content)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);render(p.parse_args().output)
