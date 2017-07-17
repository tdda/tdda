# -*- coding: utf-8 -*-

"""
Support for Pandas constraint discovery from the command-line tool
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
from tdda.constraints.pd.pdconstraints import discover_df


def discover_df_from_file(df_path, constraints_path, verbose=True, **kwargs):
    df = load_df(df_path)
    constraints = discover_df(df, **kwargs)
    output = constraints.to_json()
    if constraints_path:
        with open(constraints_path, 'w') as f:
            f.write(output)
    elif verbose:
        print(output)
    return output


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
        'inc_rex': False,
    }
    for a in args:
        if a.startswith('-'):
            if a in ('-r', '--rex'):
                params['inc_rex'] = True
            elif a in ('-R', '--norex'):
                params['inc_rex'] = False
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


class PandasDiscoverer:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def discover(self):
        params = get_params(self.argv[1:])
        if not(params['df_path']):
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        return discover_df_from_file(verbose=self.verbose, **params)


def main(argv, verbose=True):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    d = PandasDiscoverer(argv)
    d.discover()


if __name__ == '__main__':
    main(sys.argv)

