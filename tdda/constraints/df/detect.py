# -*- coding: utf-8 -*-

"""
Support for Pandas constraint detection from the command-line tool

Detect constraints using CSV files, or Pandas or R DataFrames saved as
parquet files, against a constraints from .tdda JSON constraints file.
"""

USAGE = """

Parameters:

  * input is one of:

      - a csv file
      - a .parquet file
      - any of the other supported data sources

  * constraints.tdda, if provided, is a JSON .tdda file constaining
    constraints.

  * name of output file (.csv, .parquet)
    where detection results are to be written.
    Can be - (or missing) to write to standard output.

"""

import os
import sys

from io import StringIO

import pandas as pd
import numpy as np

from tdda import __version__
from tdda.state import get_config
from tdda.constraints.flags import detect_parser, detect_flags, check_constraints_file
from tdda.constraints.df.constraints import detect_df, load_df, file_format

from tdda.utils import handle_tilde, nvl, cprint, print_stderr, tdda_path_info


def detect_df_from_file(
    df_path,
    constraints_path,
    outpath=None,
    engine=None,
    backend=None,
    verbose=True,
    **kwargs,
):
    """
    Detect records in the file provided that fail any constraints in the
    JSON ``.tdda`` file provided. This is anomaly detection.

    Args:
        df_path: Path to a file to detect against (CSV or parquet).
            Use ``None`` or ``'-'`` to read from stdin.
        constraints_path: Path to a JSON ``.tdda`` file, or an
            in-memory ``tdda.constraints.base.DatasetConstraints``
            object.
        outpath: Optional path (CSV or parquet) to write failing records
            to. ``None`` for no output.
        verbose: Controls level of output reporting.
        **kwargs: Passed to ``detect_df``.

    Returns:
        ``tdda.constraints.df.constraints.DFDetection`` object.
    """
    if df_path == '-' or df_path is None:
        df_path = StringIO(sys.stdin.read())
        if constraints_path is None:
            print('No constraints file specified.', file=sys.stderr)
            sys.exit(1)
    elif constraints_path is None:
        (stem, ext) = os.path.splitext(df_path)
        constraints_path = stem + '.tdda'
    check_constraints_file(constraints_path)

    df = load_df(df_path, engine=engine, backend=backend)
    v = detect_df(
        df,
        constraints_path,
        outpath=outpath,
        rownumber_is_index=False,
        backend=backend,
        **kwargs,
    )
    if verbose:
        cprint(v)
    return v


def df_detect_parser():
    parser = detect_parser(USAGE)
    parser.add_argument('input', help='CSV, parquet')
    parser.add_argument(
        'constraints', nargs='?', help='constraints file to verify against'
    )
    parser.add_argument(
        'outpath', nargs='?', help='file to write detection results to'
    )
    return parser


def df_detect_params(args):
    parser = df_detect_parser()
    params = {}
    flags = detect_flags(parser, args, params)
    params['df_path'] = flags.input
    params['constraints_path'] = flags.constraints
    params['outpath'] = flags.outpath
    return params


class DFDetector:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def detect(self):
        params = df_detect_params(self.argv[1:])
        path = tdda_path_info(params['df_path']).path
        if path is not None and path != '-' and not os.path.isfile(path):
            msg = f'{path} does not exist.' + (
                '\nPerhaps you are trying to mix database tables and files.'
                if ':' in path
                else ''
            )
            print_stderr(msg)
            sys.exit(1)
        return detect_df_from_file(verbose=self.verbose, **params)


def main(argv, verbose=True):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    v = DFDetector(argv)
    v.verify()


if __name__ == '__main__':
    main(sys.argv)
