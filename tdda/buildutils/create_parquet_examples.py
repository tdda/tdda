"""
Generate parquet counterparts to test csv files.

USAGE:

   python create_parquet_examples.py -f

The -f flag ("force") is to avoid refenerating these accidentally.

The key point about this is that we need these parquet files to
correspond exactly to what TDDA's default CSV reader will generate
from these CSV files, handling null and data columns exactly the same
way so that we guarantee the same behaviour.

This generates the parquet files in constraints/testdata
and also copies them to examples, then zips all the accounts files
into accounts.zip there.
"""

import os
import sys
import zipfile

from tdda.referencetest.checkpandas import default_csv_loader


BASEDIR = os.path.dirname(os.path.dirname(__file__))
TESTDIR = os.path.join(BASEDIR, 'constraints', 'testdata')
EXAMPLESDIR = os.path.join(BASEDIR, 'constraints', 'examples')

FILES = [
    'elements92.csv',
    'elements118.csv',
    'accounts1k.csv',
    'accounts25k.csv',
]


def create_parquet_files():
    accounts_files = []
    for name in FILES:
        inpath = os.path.join(TESTDIR, name)
        outpath = os.path.splitext(inpath)[0] +  '.parquet'
        df = default_csv_loader(inpath)
        df.to_parquet(outpath)
        if name.startswith('accounts'):
            accounts_files.extend([inpath, outpath])
    return accounts_files

def zip_for_examples(accounts_files):
    zippath = os.path.join(EXAMPLESDIR, 'accounts.zip')
    print(f'Writing {zippath}:')
    with zipfile.ZipFile(zippath, 'w') as z:
        for path in accounts_files:
            name = os.path.basename(path)
            z.write(path, arcname=name)
            print(f'  ... written {path} as {name}')
    print(f'Written {zippath}.')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] != '-f':
        print('USAGE: python create_parquet_examples.py -f.\n'
              'Only run this if you really know what you\'re doing!',
              file=sys.stderr)
        sys.exit(1)
    files = create_parquet_files()
    zip_for_examples(files)
