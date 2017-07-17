# -*- coding: utf-8 -*-

"""
Support for Pandas constraint verification from the command-line tool
"""

from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd
import numpy as np


USAGE = (__doc__.replace('Usage::', 'Usage:')
                .replace(':py:mod:`feather`', 'feather')
                .replace(':py:const:`csv.QUOTE_MINIMAL`',
                         'csv.QUOTE_MINIMAL'))

try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None
    try:
        import feather as feather
    except ImportError:
        feather = None

from tdda import __version__
from tdda.referencetest.checkpandas import default_csv_loader
from tdda.constraints.ext_pandas.pdconstraints import verify_df


def verify_df_from_file(df_path, constraints_path, verbose=True, **kwargs):
    df = load_df(df_path)
    v = verify_df(df, constraints_path, **kwargs)
    if verbose:
        print(v)
    return v


def load_df(path):
    if os.path.splitext(path)[1] != '.feather':
        return default_csv_loader(path)
    elif featherpmm:
        ds = featherpmm.read_dataframe(path)
        return ds.df
    elif feather:
        return feather.read_dataframe(path)
    else:
        raise Exception('pdverify requires feather to be available.\n'
                        'Use:\n    pip install feather-format\n'
                        'to add capability.\n', file=sys.stderr)


def get_params(args):
    params = {
        'df_path': None,
        'constraints_path': None,
        'report': 'all',
        'one_per_line': False,
        'ascii': False,
    }
    for a in args:
        if a.startswith('-'):
            if a in ('-a', '--all'):
                params['report'] = 'all'
            elif a in ('-f', '--fields'):
                params['report'] = 'fields'
            elif a in ('-c', '--constraints'):
                params['report'] = 'constraints'
            elif a in ('-1', '--oneperline'):
                params['one_per_line'] = True
            elif a in ('-7', '--ascii'):
                params['ascii'] = True
            else:
                usage_error()
        elif params['df_path'] is None:
            params['df_path'] = a
        elif params['constraints_path'] is None:
            params['constraints_path'] = a
        else:
            usage_error()
    return params


def usage_error():
    print(USAGE, file=sys.stderr)
    sys.exit(1)


class PandasVerifier:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def verify(self):
        params = get_params(self.argv[1:])
        if not(params['df_path']):
            print(USAGE, file=sys.stderr)
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

