# -*- coding: utf-8 -*-

"""
Support for Pandas constraint discovery from the command-line tool

Discover TDDA constraints for CSV files, and for Pandas or R DataFrames saved
as parquetfiles, and save the generated constraints as a .tdda JSON file.
"""

USAGE = """
Parameters:

  * input is one of:

    - a csv file
    - a .parquet file
    - any of the other supported data sources

  * constraints.tdda, if provided, specifies the name of a file to
    which the generated constraints will be written.  Can be - (or missing)
    to write to standard output.

"""

import os
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from tdda import __version__
from tdda.constraints.flags import discover_parser, discover_flags
from tdda.constraints.pd.constraints import (
    discover_df,
    load_df,
    write_constraints,
)

from tdda.utils import handle_tilde, nvl, tdda_path_info


def discover_df_from_file(
    df_path,
    constraints_path,
    report_path=None,
    report_formats=None,
    engine=None,
    backend=None,
    verbose=True,
    **kwargs,
):
    """
    Automatically discover potentially useful constraints that characterize
    the data provided in the file.

    Args:
        df_path: Path to a file to discover from (CSV or parquet).
            Use ``'-'`` to read from stdin.
        constraints_path: Path to write the constraints to. ``None``
            means do not write; ``'-'`` sends to stdout.
        report_path: Path for reports (extension ignored). Writes report
            variants of this path; falls back to ``constraints_path``.
        report_formats: List of report formats to write. Options:
            ``'html'``, ``'md'``, ``'txt'``, ``'yaml'``, ``'json'``,
            ``'toml'``.
        verbose: Controls level of output reporting.
        **kwargs: Passed to ``discover_df``.

    Returns:
        ``tdda.constraints.base.DatasetConstraints`` object.
    """
    md_df_path = df_path
    if df_path == '-':
        df_path = StringIO(sys.stdin.read())
        md_df_path = None
    df = load_df(df_path, backend=backend)
    return discover_df(
        df,
        constraints_path,
        df_path=md_df_path,
        report_path=report_path,
        report_formats=report_formats,
        **kwargs,
    )


def pd_discover_parser():
    parser = discover_parser(USAGE)
    parser.add_argument('input', nargs=1, help='CSV or parquet file')
    parser.add_argument(
        'constraints', nargs='?', help='name of constraints file to create'
    )
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
        path = params.get('df_path')
        pi = tdda_path_info(path)
        if path is not None and pi.path != '-' and not os.path.isfile(pi.path):
            print('%s does not exist' % pi.path)
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
