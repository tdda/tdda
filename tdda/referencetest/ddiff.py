import sys

from tdda.referencetest.checkpandas import (
    PandasComparison,
    same_structure_dataframe_diffs
)
from tdda.config import Config

import argparse

from rich import print as rprint
from rich.console import Console

USAGE = '''
USAGE: tdda diff LEFT.parquet RIGHT.parquet [MAX_DIFFS [DPS]]
   or: tdda diff LEFT.csv RIGHT.csv [MAX_DIFFS [DPS]]
'''

DEFAULT_PRECISION = 7
DEFAULT_DPS = 7


def ddiff_helper_orig(args):
    if len(args) < 2 or len(args) > 4:
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    else:
        if len(args) >= 3:
            try:
                n = int(args[2])
            except ValueError:
                print(USAGE, file=sys.stderr)
                sys.exit(1)
        else:
            n = None
        if len(args) >= 4:
            try:
                dps = int(args[3])
            except ValueError:
                print(USAGE, file=sys.stderr)
        else:
            dps = 6
        ddiff(*(args[:2]), n, dps)


TDDA_DIFF_HELP = '''
Notes
'''

class TDDADiff:
    def __init__(self, args, config=None):
        #self.config = config or Config()
        self.args = args
        self.process_args()

    def ddiff(self):
        c = PandasComparison()
        dfL = c.load_serialized_dataframe(self.left)
        dfR = c.load_serialized_dataframe(self.right)
        result = c.check_dataframe(dfL, dfR, create_temporaries=False,
                                   check_data=self.fields,
                                   type_matching='medium',
                                   precision=self.precision)

        if result.failures > 0:
            print(result.diffs)
            diff = result.diffs.dfd.diff  # there if same structure
            if diff:
                table = diff.details_table(dfL, dfR, self.maxdiffs)
                print()
                # rprint(table)
                console = Console(soft_wrap=True)
                console.print(table)




    def process_args(self):
        parser = self.parser()
        #print(222, self.args)
        flags, more = parser.parse_known_args(self.args)
        #print(333, flags)
        #print(555, flags.no_config)
        self.config = Config(load=not flags.no_config)
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
        return parser


def ddiff_helper(args):
    tddadiff = TDDADiff(args)
    #print(111, args)
    tddadiff.ddiff()


if __name__ == '__main__':
    ddiff_helper(sys.argv)


