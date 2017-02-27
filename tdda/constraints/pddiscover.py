# -*- coding: utf-8 -*-

"""
*pddiscover*
------------

Discover TDDA constraints for DataFrames saved as :py:mod:`feather` datasets,
and save generated constraints as a JSON file.

Usage::

    pddiscover df.feather [constraints.tdda]

or::

    python -m tdda.constraints.pddiscover df.feather [constraints.tdda]

where

  * *df.feather* is a :py:mod:`feather` file containing a DataFrame,

  * *constraints.tdda*, if provided, is a JSON *.tdda* file to
    which the generated constraints will be written.
"""

from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd
import numpy as np

USAGE = __doc__.replace('Usage::', 'Usage:').replace(':py:mod:`feather`',
                                                     'feather')

try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None
    try:
        import feather as feather
    except ImportError:
        print('pdverify requires feather to be available.\n'
              'Use:\n    pip install feather-format\nto add capability.\n',
              file=sys.stderr)
        raise

from tdda.constraints.pdconstraints import discover_constraints


def discover_feather_df(df_path, constraints_path, **kwargs):
    df = load_df(df_path)
    constraints = discover_constraints(df)
    if constraints_path:
        with open(constraints_path, 'w') as f:
            f.write(constraints.to_json())
    else:
        print(constraints.to_json())


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
    }
    for a in args:
        if params['df_path'] is None:
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
    if not(params['df_path']):
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    discover_feather_df(**params)

