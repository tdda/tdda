# -*- coding: utf-8 -*-

"""
Support for Pandas constraint discovery from the command-line tool

Discover TDDA constraints for CSV files, and for Pandas or R DataFrames saved
as feather files, and save the generated constraints as a .tdda JSON file.
"""

from __future__ import division
from __future__ import print_function

USAGE = '''

Parameters:

  * input is one of:

    - a csv file
    - a .feather file containing a saved Pandas or R DataFrame

  * constraints.tdda, if provided, specifies the name of a file to
    which the generated constraints will be written.

'''

import os
import sys

try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None
    try:
        import feather as feather
    except ImportError:
        feather = None

from tdda import __version__
from tdda.constraints.flags import discover_parser, discover_flags
from tdda.constraints.pd.constraints import discover_df, load_df


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


def pd_discover_parser():
    parser = discover_parser(USAGE)
    parser.add_argument('input', nargs=1, help='CSV or feather file')
    parser.add_argument('constraints', nargs='?',
                        help='name of constraints file to create')
    return parser


def pd_discover_params(args):
    parser = pd_discover_parser()
    params = {}
    flags = discover_flags(parser, args, params)
    params['df_path'] = flags.input[0] if flags.input else None
    params['constraints_path'] = (flags.constraints if flags.constraints
                                  else None)
    return params


class PandasDiscoverer:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def discover(self):
        params = pd_discover_params(self.argv[1:])
        if not(params['df_path']):
            print(USAGE, file=sys.stderr)
            sys.exit(1)
        elif not os.path.isfile(params['df_path']):
            print('%s does not exist' % params['df_path'])
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

