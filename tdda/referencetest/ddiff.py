import os
import sys

import numpy as np
import pandas as pd

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.checkpolars import PolarsComparison
from tdda.state import get_config
from tdda.utils import (
    nvl, warn, error, stdout_console as console, is_sequence,
    find_free_name
)
from tdda.utils import debug, listify
from tdda.commonflags import process_pandas_flags, add_pandas_flags
from tdda.abstractdf import col_names, calc_nunique


import argparse

from rich import print as rprint

USAGE = '''
USAGE: tdda diff LEFT.parquet RIGHT.parquet [MAX_DIFFS [DPS]]
   or: tdda diff LEFT.csv RIGHT.csv [MAX_DIFFS [DPS]]
'''

DEFAULT_PRECISION = 7
DEFAULT_DPS = 7

TDDA_DIFF_HELP = '''
Notes
'''


class TDDADiff:
    def __init__(self, left=None, right=None, precision=None,
                 vertical=False, fields=None, xfields=None,
                 type_checking=None, maxdiffs=None,
                 engine=None, backend=None, key=None, auto_key=False,
                 cli_args=None, config=None, verbosity=1):
        self.args = cli_args
        self.dconfig = get_config().tddadiff
        self.type_checking = self.dconfig.type_checking
        self.left = left
        self.right = right
        self.precision = precision
        self.vertical = vertical
        self.fields = fields
        self.xfields = xfields
        self.maxdiffs = maxdiffs
        self.engine = engine
        self.backend = backend
        self.key = key
        self.auto_key = auto_key
        self.verbosity = verbosity
        if cli_args:
            self.process_args()


    def ddiff(self):
        c = (
            PandasComparison()
            if self.engine == 'pandas'
            else PolarsComparison()
        )
        dfL = c.load_serialized_dataframe(self.left)
        dfR = c.load_serialized_dataframe(self.right)
        result = c.check_dataframe(dfL, dfR, create_temporaries=False,
                                   check_data=self.fields,
                                   type_matching=self.type_checking,
                                   precision=self.precision,
                                   backend=self.backend, key=self.key)

        if result.failures > 0:
            print(result.diffs)
            diff = result.diffs.dfd.diff  # there if same structure
                                          # or close enough
            if diff:
                table = diff.details_table(dfL, dfR, self.maxdiffs)
                if table:
                    print()
                    console.print(table)
        elif self.verbosity > 1:
            print('No differences.')


    def process_args(self):
        parser = self.parser()
        flags, more = parser.parse_known_args(self.args)
        self.config = get_config(force_no_global=flags.no_config)
        p = self.config.referencetest
        self.fields = None

        if more:
            s = 's' if len(more) > 1 else ''
            unks = ','.join(more)
            self.error('Unknown argument%s: %s' % (s, unks))

        self.__dict__.update(vars(flags))

        if not self.left:
            self.error('No input data specified.')

        if not self.right:
            self.error('No output data specified.')


        if self.dps and self.precision is None:
            self.precision = self.dps

        if self.colours:
            colours = [c.strip() for c in self.colours.lower().split('-')]
            if len(colours) != 2:
               self.error('Form: --colours left-right.')
            p.set_colours(*colours)
        if self.bw:
            p.bw = True
        if self.mono:
            p.mono = True
        if self.LR:
            p.set_prefixes('L: ', 'R: ')
        if self.AE:
            p.set_prefixes('A: ', 'E: ')
        if self.angles:
            p.set_prefixes('< ', '> ')
        if self.pm:
            p.set_prefixes('+ ', '- ')
        if self.prefixes:
            prefixes = self.prefixes.split('-')
            if len(prefixes) != 2:
               self.error('Form: --prefixes left-right.')
            p.set_prefixes(*prefixes)

        if self.horizontal:
            if self.vertical:
               self.error('Cannot use --horizontal and --vertical together.')
            else:
                p.vertical = False
        elif self.vertical:
            p.vertical = True

        if self.fields:
            self.fields = [f.strip() for f in self.fields.split(', ')]
        if self.xfields:
            self.fields = lambda df: (
                set(df) - set(f.strip() for f in self.xfields.split(','))
            )

        if (  (self.strict and 1)
            + (self.medium and 1)
            + ((self.permissive or self.loose) and 1)
        ) > 1:
            warn('Only one of --strict, --medium and --loose should '
                 'be given.\nUsing medium (default).')
        elif self.strict:
            self.type_checking = 'strict'
        elif self.medium:
            self.type_checking = 'medium'
        elif self.permissive or self.loose:
            self.type_checking = 'loose'

        self.engine, self.backend = process_pandas_flags(self)


    def error(self, msg):
        print(msg, file=sys.stderr)
        sys.exit(1)

    def parser(self):
        formatter = argparse.RawDescriptionHelpFormatter
        parser = argparse.ArgumentParser(prog='tdda diff',
                                         epilog=TDDA_DIFF_HELP,
                                         formatter_class=formatter)

        parser.add_argument('left', help='left/actual data (CSV/parquet)')
        parser.add_argument('right', nargs='?',
                            help='right/expected/reference data (CSV/parquet)')
        parser.add_argument('outpath', nargs='?',
                            help='file to which to write differences')

        parser.add_argument('-?', '--?', action='help',
                            help='same as -h or --help')

        parser.add_argument('--dps', type=int, default=DEFAULT_DPS,
            help='Number of decimal places to show for floating-point values.'
                 '\nAlso sets precision if not specified separately')

        parser.add_argument('--precision', type=int, default=DEFAULT_PRECISION,
            help='Precision for floating point comparisons. '
                 'Two floats a and b will be '
                 'considered equal if abs(a - b) < 1e-n,'
                 'where n is the specified precision')

        parser.add_argument('--maxdiffs', type=int, default=None,
            help='Maximum number of differences to show.')

        parser.add_argument('--mono', action='store_true',
            help='Show monochrome output. Also enables --LR by default')

        parser.add_argument('--bw', action='store_true',
            help='Show black and white output. Also enables --LR by default')

        parser.add_argument('--AE', action='store_true',
            help='Use A: and E: as labels for the two datasets')

        parser.add_argument('--LR', action='store_true',
            help='Use L: and R: as labels for the two datasets')

        parser.add_argument('--angles', action='store_true',
            help='Use < and > as labels for the two datasets')

        parser.add_argument('--pm', action='store_true',
            help='Use + and - as labels for the two datasets')

        parser.add_argument('--prefixes', type=str, action='store',
            help='Use prefixes specified as labels for the two datasets, '
                 'e.g. --prefixes "actual: -ref: "')

        parser.add_argument('--colours', '-c', '--colours', type=str,
                             action='store',
            help='Use colours specified e.g. -c red-blue')

        parser.add_argument('--horizontal', '-H', action='store_true',
            help='Force horizontal dispay')

        parser.add_argument('--vertical', '-V', action='store_true',
            help='Force vertical dispay')

        parser.add_argument('--fields', type=str, action='store',
            help='Check only these fields (comma-separated list)')

        parser.add_argument('--xfields', type=str, action='store',
            help='Check all fields except these (comma-separated list)')

        parser.add_argument('--no-config', action='store_true',
            help='Use default configuration (ignore ~/.tdda.toml)')

        parser.add_argument('--strict', action='store_true',
            help='Use strict type comparisons')

        parser.add_argument('--medium', action='store_true',
            help='Use medium type comparisons')

        parser.add_argument('--loose', action='store_true',
            help='Use loose (permissive) type comparisons')

        parser.add_argument('--permissive', action='store_true',
            help='Use loose (permissive) type comparisons')
        add_pandas_flags(parser)
        return parser


def find_usable_key(left, right, key=None, verbosity=1):
    """
    If key is supplied, this adds a row number to (copied of) the
    left and right DataFrames, at the start.

    If key is Truthy, this tries to find a common key to use for the outer
    join for diffing. If it fails, it falls back to using row index.

    If key is Falsy:
        If the DataFrames have the same length, this does nothing.
        If they have different lengths, a row number is added to them both.

    Args:
        left:   a DataFrame (currently Pandas)
        right:  a DataFrame (currently Pandas)
        key:    One of:

                    a field in left and right, to use as a join key

                    a list of fields, in left and right, to use as a join key

                    True: meaning that a join key should be found

                    None (or other falsy value) means just use row number
                    as the join key.

       Returns:
            (left, right, key):  The left and right and DataFrames are
                                 copies of left and right with an extra
                                 column, if that has been created.

                                 The key is the key found, to be used,
                                 if a key is created and found.
    """
    nL, nR = left.shape[0], right.shape[0]
    if isinstance(key, str) or is_sequence(key):
        check_is_usable_key(left, right, key, raise_if_not=True)
        mode = 'key'   # key provided
    elif key == True:

        mode = 'find'   # try to find a key
    elif key:
        error(f'Unexpected value for key value: {repr(key)}')
    elif nL == nR:
        mode = 'common'  # same length, no key needed
    else:
        mode = 'rownum'  # Add row number and use as key

    if mode == 'find':
        key = find_common_key(left, right, verbosity=verbosity)
        if key is None:
            mode = 'common' if nL == nR else 'rownum'

    if key or nL != nR:
        all_names = set(col_names(left)) | set(col_names(right))
        key = find_free_name(all_names, ['Row', 'ROW', 'row', 'Row#'])
        L = pd.DataFrame({key: pd.Series(np.arange(left.shape[0]),
                                         dtype='Int64')})
        for k in left:
            L[k] = left[k]
        R = pd.DataFrame({key: pd.Series(np.arange(right.shape[0]),
                                         dtype='Int64')})
        for k in right:
            R[k] = right[k]
        left, right = L, R

        left.columns = [name + '_L' for name in left]
        right.columns = [name + '_R' for name in right]

        keyL, keyR = key + '_L', key + '_R'
        dfj = left.merge(right, left_on=keyL, right_on=keyR, how='outer')

        L = dfj[left.columns]
        R = dfj[right.columns]
        L.columns = [c[:-2] for c in L]
        R.columns = [c[:-2] for c in R]
    else:
        L, R = left, right

    return L, R, key


def find_common_key(left, right, verbosity=1):
    nL, nR = left.shape[0], right.shape[0]
    right_cols = set(col_names(right))
    shared_cols = [k for k in col_names(left) if k in right_cols]
    distincts = {}
    for key in shared_cols:
        ndL = calc_nunique(left[key])
        if ndL == nL:
            ndR = calc_nunique(right[key])
            if ndR == nR:
                return key
        distincts[key] = ndL
    if len(distincts) >= 2:
        cands = sorted(shared_cols, key = lambda k: -distincts[k])
        for i, key1 in enumerate(cands[:-1]):
            for key2 in cands[i + 1:]:
                keys = [key1, key2]
                L = left[keys].groupby(keys).count().reset_index()
                if L.shape[0] == nL:
                    R = right[keys].groupby(keys).count().reset_index()
                    if R.shape[0] == nR:
                        return keys

    warn('No usable key find. Use row number.', verbose=verbosity > 0)
    return None


def check_is_usable_key(left, right, key, raise_if_not=False):
    keys = listify(key)
    str_key = ','.join(key)
    nL, nR = left.shape[0], right.shape[0]
    L = left[keys].groupby(keys).count().reset_index()
    if L.shape[0] == nL:
        R = right[keys].groupby(keys).count().reset_index()
        if R.shape[0] == nR:
            return True
        elif raise_if_not:
             error(f'{str_key} is not a primary key for in right DataFrame.')
        else:
            return False
    elif raise_if_not:
        error(f'{str_key} is not a primary key for in left DataFrame.')
    return False



def ddiff_helper(args):
    tddadiff = TDDADiff(cli_args=args)
    tddadiff.ddiff()



if __name__ == '__main__':
    ddiff_helper(sys.argv)
