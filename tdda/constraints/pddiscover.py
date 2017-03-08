# -*- coding: utf-8 -*-

"""
*tdda discover*
---------------

Discover TDDA constraints for DataFrames saved as :py:mod:`feather` datasets,
and save generated constraints as a JSON file.

Usage::

    tdda discover input-file [constraints.tdda]

or::

    python -m tdda.constraints.pddiscover input-file [constraints.tdda]

where

  * *input-file* is either:
        - a csv file
        - a :py:mod:`feather` file containing a DataFrame,
          with extension ``.feather``

  * *constraints.tdda*, if provided, specifies the name of a file to
    which the generated constraints will be written in JSON.

If a CSV file is used, it will be processed by the Pandas CSV file reader
with the following settings:

 - index_col             is ``None``
 - infer_datetime_format is ``True``
 - quotechar             is ``"``
 - quoting               is :py:const:`csv.QUOTE_MINIMAL`
 - escapechar            is ``\\`` (backslash)
 - na_values             are the empty string, ``"NaN"``, and ``"NULL"``
 - keep_default_na       is ``False``

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
        print('pdverify requires feather to be available.\n'
              'Use:\n    pip install feather-format\nto add capability.\n',
              file=sys.stderr)
        raise

from tdda import __version__
from tdda.constraints.pdconstraints import discover_constraints
from tdda.referencetest.checkpandas import default_csv_loader


def discover_constraints_from_file(df_path, constraints_path, **kwargs):
    df = load_df(df_path)
    constraints = discover_constraints(df)
    if constraints_path:
        with open(constraints_path, 'w') as f:
            f.write(constraints.to_json())
    else:
        print(constraints.to_json())


def load_df(path):
    if os.path.splitext(path)[1] != '.feather':
        return default_csv_loader(path)
    elif featherpmm:
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
    if len(sys.argv) > 1 and sys.argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    params = get_params(sys.argv[1:])
    if not(params['df_path']):
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    discover_constraints_from_file(**params)

