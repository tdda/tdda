# -*- coding: utf-8 -*-

"""
Support for Pandas constraint detection from the command-line tool

Detect constraints using CSV files, or Pandas or R DataFrames saved as
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

  * name of output file (.csv or .feather) where detection results
    are to be written. Can be - (or missing) to write to standard output.

'''

import os
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

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
from tdda.constraints.flags import detect_parser, detect_flags
from tdda.constraints.pd.constraints import detect_df, load_df, file_format


def detect_df_from_file(df_path, constraints_path, outpath,
                        verbose=True, **kwargs):
    if df_path == '-' or df_path is None:
        df_path = StringIO(sys.stdin.read())
    if constraints_path is None:
        if not isinstance(df_path, StringIO):
            split = os.path.splitext(df_path)
            if split[1] in ('.csv', '.feather'):
                constraints_path = split[0] + '.tdda'
        if constraints_path is None:
            print('No constraints file specified.', file=sys.stderr)
            sys.exit(1)

    df = load_df(df_path)
    from_feather = file_format(df_path) == 'feather'
    v = detect_df(df, constraints_path, outpath=outpath,
                  rownumber_is_index=from_feather, **kwargs)
    if verbose and outpath is not None and outpath != '-':
        print(v)
    return v


def pd_detect_parser():
    parser = detect_parser(USAGE)
    parser.add_argument('input', help='CSV or feather file')
    parser.add_argument('constraints', nargs='?',
                        help='constraints file to verify against')
    parser.add_argument('outpath', nargs='?',
                        help='file to write detection results to')
    return parser


def pd_detect_params(args):
    parser = pd_detect_parser()
    params = {}
    flags = detect_flags(parser, args, params)
    params['df_path'] = flags.input
    params['constraints_path'] = flags.constraints
    params['outpath'] = flags.outpath
    return params


class PandasDetector:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def detect(self):
        params = pd_detect_params(self.argv[1:])
        path = params['df_path']
        if path is not None and path != '-' and not os.path.isfile(path):
            print('%s does not exist' % path)
            sys.exit(1)
        return detect_df_from_file(verbose=self.verbose, **params)


def main(argv, verbose=True):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    v = PandasDetector(argv)
    v.verify()


if __name__ == '__main__':
    main(sys.argv)

