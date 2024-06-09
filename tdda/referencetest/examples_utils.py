import os
import pandas as pd

from rich import print as rprint
import sys

THISDIR = os.path.dirname(__file__)
EXAMPLESDIR = os.path.join(THISDIR, 'examples', 'reference')

def make_parquet_counterparts():
    paths = [
        os.path.abspath(os.path.join(EXAMPLESDIR, f))
        for f in os.listdir(EXAMPLESDIR)
        if f.endswith('.csv')
    ]
    if not paths:
        rprint('[red]Nothing found to convert.[/red]', file=sys.stderr)
        sys.exit(1)
    else:
        for path in paths:
            df = pd.read_csv(path)
            outpath = os.path.abspath(path[:-4]) + '.parquet'
            df.to_parquet(outpath, index=False)
            print(f'Written {outpath}.')


if __name__ == '__main__':
    make_parquet_counterparts()
