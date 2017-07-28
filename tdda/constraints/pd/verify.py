# -*- coding: utf-8 -*-

"""
Support for Pandas constraint verification from the command-line tool
"""

from __future__ import division
from __future__ import print_function

USAGE = '''
Verify CSV files, or Pandas or R DataFrames saved as feather files,
against a constraints from .tdda JSON file.
constraints file.

Usage:

    tdda verify [FLAGS] input-file [constraints.tdda]

where:

  * input is one of:

      - a csv file
      - a feather file containing a Pandas or R DataFrame

  * constraints.tdda, if provided, is a JSON .tdda file constaining
    constraints.

If no constraints file is provided, a file with the same path as the
input file, with a .tdda extension will be tried.

Optional flags are:

  * -a, --all
      Report all fields, even if there are no failures
  * -f, --fields
      Report only fields with failures
  * -c, --constraints
      Report only individual constraints that fail.  Not yet implemented.
  * -1, --oneperline
      Report each constraint failure on a separate line.  Not yet implemented.
  * -7, --ascii
      Report in ASCII form, without using special characters.
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
from tdda.constraints.pd.constraints import verify_df, load_df


def verify_df_from_file(df_path, constraints_path, verbose=True, **kwargs):
    df = load_df(df_path)
    v = verify_df(df, constraints_path, **kwargs)
    if verbose:
        print(v)
    return v


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

