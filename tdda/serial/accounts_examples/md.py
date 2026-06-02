import sys

import pandas as pd
import polars as pl

from tdda.serial import csv_to_pandas, csv_to_polars


USAGE = '''
Usage: python md.py path[:] [--polars] [-r] [-a] [-n] [-o]

where
     :       on end of path forces metadata lookup and csv_to_x usage
   -r        Means raw: us pd.read_csv or pl.read_csv
   --polars  Uses polars rather than pandas
   -a        Forces arrow backend for pandas
   -n        Forces numpy_nullable backend for pandas
   -o        Forces original backend for pandas

'''


def read(name, polars, raw, backend):

    colon = name.endswith(':')
    try:
        if polars:
            if raw:
                print('Polars read_csv')
                df = pl.read_csv(name)
            else:
                print('Polars with csv_to_polars')
                df = csv_to_polars(name)
            print(describe(df))
        else:  # pandas
            if raw:
                be = backend or 'original'
                print(f'Pandas read_csv ({be})')
                kw = {} if backend is None else {'dtype_backend': backend}
                df = pd.read_csv(name, **kw)
            else:
                print('Pandas with csv_to_pandas')
                df = csv_to_pandas(name, backend='o' if backend is None else backend)
            df.info()
    except Exception as e:
        print(e)
        return
    be = 'o' if backend is None else backend
    print('=' * 78, end='\n\n')


def describe(df):
    return('\n'.join(f'{c:20} {str(df[c].count()) + " non-null count":20} {str(df[c].dtype):10} ' for c in df.columns))



if __name__ == '__main__':
    backend = 'a' if '-a' in sys.argv else 'n' if '-n' in sys.argv else None
    polars = '--polars' in sys.argv
    raw = '-r' in sys.argv
    if len(sys.argv) == 1:
        print(USAGE)
        sys.exit(1)
    read(sys.argv[1], polars=polars, raw=raw, backend=backend)
