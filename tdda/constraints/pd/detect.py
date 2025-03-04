# -*- coding: utf-8 -*-

"""
Support for Pandas constraint detection from the command-line tool

Detect constraints using CSV files, or Pandas or R DataFrames saved as
parquet files, against a constraints from .tdda JSON constraints file.
"""

USAGE = '''

Parameters:

  * input is one of:

      - a csv file
      - a .parquet file
      - any of the other supported data sources

  * constraints.tdda, if provided, is a JSON .tdda file constaining
    constraints.

  * name of output file (.csv, .parqet)
    where detection results are to be written.
    Can be - (or missing) to write to standard output.

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
from tdda.constraints.flags import detect_parser, detect_flags
from tdda.constraints.pd.constraints import detect_df, load_df, file_format

from tdda.utils import handle_tilde, nvl


def detect_df_from_file(df_path, constraints_path, outpath=None,
                        verbose=True, **kwargs):
    """
    Check the records from the Pandas DataFrame provided, to detect
    records that fail any of the constraints in the JSON ``.tdda`` file
    provided. This is anomaly detection.

    Inputs:

        *df_path*:
             Path to a file containing data to be verified.
             Normally a parquet of CSV file.

        *constraints_path*:
             The path to a JSON ``.tdda`` file.
             Alternatively, can be an in-memory
             :py:class:`~tdda.constraints.base.DatasetConstraints` object.

        *outpath*:
            Optional destination to write output records.
            Normally path for a CSV or parquet file.
            None for no output.

        *verbose*:
            Controls level of output reporting

        *kwargs*:
            Passed to discover_df

    Returns:
        :py:class:`~tdda.constraints.pd.constraints.PandasDetection` object.
    """
    if df_path == '-' or df_path is None:
        df_path = StringIO(sys.stdin.read())
        if constraints_path is None:
            print('No constraints file specified.', file=sys.stderr)
            sys.exit(1)
    elif constraints_path is None:
        (stem, ext) = os.path.splitext(df_path)
        constraints_path = stem + '.tdda'

    df = load_df(df_path)
    v = detect_df(df, constraints_path, outpath=outpath,
                  rownumber_is_index=False, **kwargs)
    if verbose and outpath is not None and outpath != '-':
        print(v)
    return v


def pd_detect_parser():
    parser = detect_parser(USAGE)
    parser.add_argument('input', help='CSV, parquet')
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
        path = handle_tilde(params['df_path'])
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

