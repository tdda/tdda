# -*- coding: utf-8 -*-

"""
*tdda verify*
-------------

Verify TDDA constraints for CSV files or DataFrames saved as
:py:mod:`feather` datasets, against a JSON constraints file.

Usage::

    tdda verify [FLAGS] input-file [constraints.tdda]

or::

    python -m tdda.constraints.pdverify [FLAGS] input-file [constraints.tdda]

where

  * *input-file* is either:
        - a csv file
        - a :py:mod:`feather` file containing a DataFrame,
          with extension ``.feather``

  * *constraints.tdda*, if provided, is a JSON *.tdda* file
    constaining constraints. If no constraints file is provided,
    a file with the same path as the input file, with a *.tdda* extension
    will be tried.

Optional flags are:

    -a, --all          Report all fields, even if there are no failures
    -f, --fields       Report only fields with failures
    -c, --constraints  Report only individual constraints that fail.
                       Not yet implemented.
    -1, --oneperline   Report each constraint failure on a separate line.
                       Not yet implemented.

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
from tdda.constraints.pdconstraints import verify_df
from tdda.referencetest.checkpandas import default_csv_loader


def verify_df_from_file(df_path, constraints_path, **kwargs):
    df = load_df(df_path)
    print(verify_df(df, constraints_path, **kwargs))


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
            elif a in ('-1', '--oneperline'):
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
    if len(sys.argv) > 1 and sys.argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    params = get_params(sys.argv[1:])
    if not(params['df_path']):
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    verify_df_from_file(**params)

