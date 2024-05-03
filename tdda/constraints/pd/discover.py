# -*- coding: utf-8 -*-

"""
Support for Pandas constraint discovery from the command-line tool

Discover TDDA constraints for CSV files, and for Pandas or R DataFrames saved
as parquetfiles, and save the generated constraints as a .tdda JSON file.
"""

USAGE = '''

Parameters:

  * input is one of:

    - a csv file
    - a .parquet file
    - any of the other supported data sources

  * constraints.tdda, if provided, specifies the name of a file to
    which the generated constraints will be written.  Can be - (or missing)
    to write to standard output.

'''

import os
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from tdda import __version__
from tdda.constraints.flags import discover_parser, discover_flags
from tdda.constraints.pd.constraints import discover_df, load_df


def discover_df_from_file(df_path, constraints_path, verbose=True, **kwargs):
    md_df_path = df_path
    if df_path == '-':
        df_path = StringIO(sys.stdin.read())
        md_df_path = None
    df = load_df(df_path)
    constraints = discover_df(df, df_path=md_df_path, **kwargs)
    if constraints is None:
        # should never happen
        return

    output = constraints.to_json(tddafile=constraints_path)
    if constraints_path and constraints_path != '-':
        with open(constraints_path, 'w') as f:
            f.write(output)
    elif verbose or constraints_path == '-':
        print(output)
    return output


def pd_discover_parser():
    parser = discover_parser(USAGE)
    parser.add_argument('input', nargs=1,
                        help='CSV or parquet file')
    parser.add_argument('constraints', nargs='?',
                        help='name of constraints file to create')
    return parser


def pd_discover_params(args):
    parser = pd_discover_parser()
    params = {}
    flags = discover_flags(parser, args, params)
    params['df_path'] = flags.input[0] if flags.input else None
    params['constraints_path'] = flags.constraints
    return params


class PandasDiscoverer:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def discover(self):
        params = pd_discover_params(self.argv[1:])
        path = params['df_path']
        if path is not None and path != '-' and not os.path.isfile(path):
            print('%s does not exist' % path)
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

