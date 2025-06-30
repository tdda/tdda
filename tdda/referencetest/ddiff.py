import os
import sys

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.checkpolars import PolarsComparison
from tdda.state import get_config
from tdda.utils import warn, error, stdout_console as console
from tdda.state import get_config

import argparse

from rich import print as rprint

USAGE = '''
USAGE: tdda diff LEFT.parquet RIGHT.parquet [MAX_DIFFS [DPS]]
   or: tdda diff LEFT.csv RIGHT.csv [MAX_DIFFS [DPS]]
'''

DEFAULT_PRECISION = 7
DEFAULT_DPS = 7

ENGINES = {
    'pandas': 'pandas',
    'polars': 'polars',

    'pd': 'pandas',
    'pl': 'polars',
}


TDDA_DIFF_HELP = '''
Notes
'''


class TDDADiff:
    def __init__(self, args, config=None):
        self.args = args
        self.dconfig = get_config().tddadiff
        self.type_checking = self.dconfig.type_checking
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
                                   precision=self.precision)

        if result.failures > 0:
            print(result.diffs)
            diff = result.diffs.dfd.diff  # there if same structure
                                          # or close enough
            if diff:
                table = diff.details_table(dfL, dfR, self.maxdiffs)
                if table:
                    print()
                    console.print(table)


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

        engine = ENGINES.get(self.engine, self.config.engine)
        if engine is None:
            warn(f'Engine "{self.engine}" unknown. Using {c.engine} '
                 'from config.')
        else:
            self.engine = self.config.engine = engine

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

        parser.add_argument('--engine', '-e', type=str, action='store',
            help='Dataframe engine (pandas or polars)')

        return parser


def ddiff_helper(args):
    tddadiff = TDDADiff(args)
    tddadiff.ddiff()




if __name__ == '__main__':
    ddiff_helper(sys.argv)
