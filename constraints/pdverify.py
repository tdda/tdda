# -*- coding: utf-8 -*-

"""
pdverify.py: verify TDDA constraints for feather dataset
"""

from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd
import numpy as np

USAGE = """Usage:

    pdverify df.feather [constraints.tdda]

where df.feather is a feather file containing a dataframe.
If constraints.tdda is provided, this is a JSON .tdda file
constaining constraints. If no constraints file is provided,
a file with the same path as the feather file, a .tdda extension
will be tried.
"""

try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None
    try:
        import feather as feather
    except ImportError:
        print('pdverify required feather to be available.\n'
              'Use:\n    pip install feather\nto add capability.\n',
              file=sys.stderr)
        raise

from tdda.constraints.base import DatasetConstraints
from tdda.constraints.pdconstraints import PandasConstraintVerifier, verify_df


def verify_feather_df(df_path, constraints_path, **kwargs):
    df = load_df(df_path)
    print(verify_df(df, constraints_path, **kwargs))


def load_df(path):
    if featherpmm:
        ds = featherpmm.read_dataframe(path)
        return ds.df
    else:
        return feather.read_dataframe(path)


def get_params(args):
    params = {
        'df_path': None,
        'constraints_path': None,
        'report': 'all',
        'one_per_line': False,
    }
    for a in args:
        if a.startswith('-'):
            if a in ('-a', '--all'):
                params['report'] = 'all'
            elif a in ('-f', '--fields'):
                params['report'] = 'fields'
            elif a in ('-c', '--constraints'):
                params['report'] = 'constraints'
            elif a in ('1', 'oneperline'):
                params['one_per_line'] = True
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


if __name__ == '__main__':
    params = get_params(sys.argv[1:])
    if not(params['constraints_path']):
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    verify_feather_df(**params)

