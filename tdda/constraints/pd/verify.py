# -*- coding: utf-8 -*-

"""
Support for Pandas constraint verification from the command-line tool

Verify constraints using CSV files, or Pandas or R DataFrames saved as
parquet files, against a constraints from .tdda JSON constraints file.
"""

USAGE = '''

Parameters:

  * input is one of:

      - a csv file. Can be - to read from standard input.
      - a parquet file
      - any of the other supported data sources

  * constraints.tdda, if provided, is a JSON .tdda file constaining
    constraints.

If no constraints file is provided, a file with the same path as the
input file, with a .tdda extension will be tried.

'''

import os
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import pandas as pd
import numpy as np

from tdda import __version__
from tdda.constraints.flags import verify_parser, verify_flags
from tdda.constraints.pd.constraints import verify_df, load_df


def verify_df_from_file(df_path, constraints_path, verbose=True, **kwargs):
    if df_path == '-' or df_path is None:
        df_path = StringIO(sys.stdin.read())
        if constraints_path is None:
            print('No constraints file specified.', file=sys.stderr)
            sys.exit(1)
    if constraints_path is None:
        stem, ext = os.path.splitext(df_path)
        constraints_path = stem + '.tdda'

    df = load_df(df_path)
    v = verify_df(df, constraints_path, **kwargs)
    if verbose:
        print(v)
    return v


def pd_verify_parser():
    parser = verify_parser(USAGE)
    parser.add_argument('input', nargs=1, help='CSV or parquet file')
    parser.add_argument('constraints', nargs='?',
                        help='constraints file to verify against')
    return parser


def pd_verify_params(args):
    parser = pd_verify_parser()
    params = {}
    flags = verify_flags(parser, args, params)
    params['df_path'] = flags.input[0] if flags.input else None
    params['constraints_path'] = flags.constraints
    return params


class PandasVerifier:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def verify(self):
        params = pd_verify_params(self.argv[1:])
        path = params['df_path']
        if path is not None and path != '-' and not os.path.isfile(path):
            print('%s does not exist' % path)
            sys.exit(1)
        return verify_df_from_file(verbose=self.verbose, **params)


def main(argv, verbose=True):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    v = PandasVerifier(argv)
    v.verify()


if __name__ == '__main__':
    main(sys.argv)

