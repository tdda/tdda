# -*- coding: utf-8 -*-

"""
Support for Pandas constraint verification from the command-line tool

Verify constraints using CSV files, or Pandas or R DataFrames saved as
feather files, against a constraints from .tdda JSON constraints file.
"""

from __future__ import division
from __future__ import print_function

USAGE = '''

Parameters:

  * input is one of:

      - a csv file
      - a feather file containing a Pandas or R DataFrame

  * constraints.tdda, if provided, is a JSON .tdda file constaining
    constraints.

If no constraints file is provided, a file with the same path as the
input file, with a .tdda extension will be tried.

'''

import os
import sys

import pandas as pd
import numpy as np

try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None
    try:
        import feather as feather
    except ImportError:
        feather = None

from tdda import __version__
from tdda.constraints.flags import verify_parser, verify_flags
from tdda.constraints.pd.constraints import verify_df, load_df


def verify_df_from_file(df_path, constraints_path, verbose=True, **kwargs):
    df = load_df(df_path)
    v = verify_df(df, constraints_path, **kwargs)
    if verbose:
        print(v)
    return v


def pd_verify_parser():
    parser = verify_parser(USAGE)
    parser.add_argument('input', nargs=1, help='CSV or feather file')
    parser.add_argument('constraints', nargs=1,
                        help='constraints file to verify against')
    return parser


def pd_verify_params(args):
    parser = pd_verify_parser()
    params = {}
    flags = verify_flags(parser, args, params)
    params['df_path'] = flags.input[0] if flags.input else None
    params['constraints_path'] = (flags.constraints[0] if flags.constraints
                                  else None)
    return params


class PandasVerifier:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def verify(self):
        params = pd_verify_params(self.argv[1:])
        if not(params['df_path']):
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        elif not os.path.isfile(params['df_path']):
            print('%s does not exist' % params['df_path'])
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

