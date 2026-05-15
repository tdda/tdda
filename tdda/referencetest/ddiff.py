import sys

import pandas as pd
import polars as pl

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.checkpolars import PolarsComparison
from tdda.referencetest.diffutils import (
    find_usable_key,
)
from tdda.state import get_config
from tdda.utils import (
    nvl,
    stdout_console,
    split_string_list,
    warn,
    debug,
)
from tdda.commonflags import process_pandas_flags, add_pandas_flags
from tdda.abstractdf import (
    filter_fields,
)


import argparse

USAGE = """
USAGE: tdda diff LEFT.parquet RIGHT.parquet [MAX_DIFFS [DPS]]
   or: tdda diff LEFT.csv RIGHT.csv [MAX_DIFFS [DPS]]
"""

DEFAULT_PRECISION = 7
DEFAULT_DPS = 7

TDDA_DIFF_HELP = """
Notes
"""


class TDDADiff:
    def __init__(
        self,
        config,
        left=None,
        right=None,
        precision=None,
        vertical=False,
        fields=None,
        xfields=None,
        type_checking=None,
        maxdiffs=None,
        engine=None,
        backend=None,
        key=None,
        auto_key=False,
        cli_args=None,
        console=None,
        quick=False,
        verbosity=1,
    ):
        self.args = cli_args
        self.config = config
        self.dconfig = self.config.tddadiff
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
        self.find_md = self.dconfig.find_md
        self.quick = quick
        self.dflib = self.df_or_pl(pd, pl)
        self.console = console or stdout_console

        if cli_args:
            self.process_args()

    def df_or_pl(self, if_pd, if_pl):
        """
        Returns if_pd if the engine is pandas, otherwise if_pl
        """
        return if_pd if self.is_pandas() else if_pl

    def is_pandas(self):
        return self.engine == 'pandas'

    def ddiff(self):
        Comp = PandasComparison if self.is_pandas() else PolarsComparison
        c = Comp(config=self.config)
        kw = {'infer_datetime_formats': True}
        dfL = c.load_serialized_dataframe(
            self.left, find_md=self.find_md, **kw
        )
        dfR = c.load_serialized_dataframe(
            self.right, find_md=self.find_md, **kw
        )
        dfL = filter_fields(dfL, self.fields, self.xfields)
        dfR = filter_fields(dfR, self.fields, self.xfields)
        dfL, dfR, key = find_usable_key(self.is_pandas(), dfL, dfR, self.key)
        result = c.check_dataframe(
            dfL,
            dfR,
            create_temporaries=False,
            check_data=self.fields,
            type_matching=self.type_checking,
            precision=self.precision,
            backend=self.backend,
            key=self.key,
            quick=self.quick,
        )

        if result.failures > 0:
            self.console.print(result.diffs)
            diff = result.diffs.dfd.diff  # there if same structure
            # or close enough
            if diff:
                table = diff.details_table(
                    nvl(result.df, dfL), nvl(result.ref_df, dfR), self.maxdiffs
                )
                if table:
                    self.console.print()
                    self.console.print(table)
            return True
        elif self.verbosity > 1:
            print('No differences.')
        return False

    def process_args(self):
        parser = self.parser()
        flags, more = parser.parse_known_args(self.args)
        p = self.config.referencetest
        self.fields = None

        if more:
            s = 's' if len(more) > 1 else ''
            unks = ','.join(more)
            self.error('Unknown argument%s: %s' % (s, unks), code=2)

        self.__dict__.update(vars(flags))

        if not self.left:
            self.error('No input data specified.', code=2)

        if not self.right:
            self.error('No output data specified.', code=2)

        if self.dps and self.precision is None:
            self.precision = self.dps

        if self.colours:
            colours = [c.strip() for c in self.colours.lower().split('-')]
            if len(colours) != 2:
                self.error('Form: --colours left-right.', code=2)
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
                self.error('Form: --prefixes left-right.', code=2)
            p.set_prefixes(*prefixes)

        if self.horizontal:
            if self.vertical:
                self.error('Cannot use --horizontal and --vertical together.', code=2)
            else:
                p.vertical = False
        elif self.vertical:
            p.vertical = True

        if self.fields:
            self.fields = [f.strip() for f in self.fields.split(',')]

        if self.xfields:
            self.xfields = [f.strip() for f in self.xfields.split(', ')]

        if self.key:
            self.key = split_string_list(self.key)
        if self.find_md_flag:
            self.find_md = True
        elif self.no_md:
            self.find_md = False

        if (
            (self.strict and 1)
            + (self.medium and 1)
            + ((self.permissive or self.loose) and 1)
        ) > 1:
            warn(
                'Only one of --strict, --medium and --loose should '
                'be given.\nUsing medium (default).'
            )
        elif self.strict:
            self.type_checking = 'strict'
        elif self.medium:
            self.type_checking = 'medium'
        elif self.permissive or self.loose:
            self.type_checking = 'loose'

        self.engine, self.backend = process_pandas_flags(self.config, self)

    def error(self, msg, code=1):
        print(msg, file=sys.stderr)
        sys.exit(code)

    def parser(self):
        formatter = argparse.RawDescriptionHelpFormatter
        parser = argparse.ArgumentParser(
            prog='tdda diff', epilog=TDDA_DIFF_HELP, formatter_class=formatter
        )

        parser.add_argument('left', help='left/actual data (CSV/parquet)')
        parser.add_argument(
            'right',
            nargs='?',
            help='right/expected/reference data (CSV/parquet)',
        )
        parser.add_argument(
            'outpath', nargs='?', help='file to which to write differences'
        )

        parser.add_argument(
            '-?', '--?', action='help', help='same as -h or --help'
        )

        parser.add_argument(
            '--dps',
            type=int,
            default=DEFAULT_DPS,
            help='Number of decimal places to show for floating-point values.'
            '\nAlso sets precision if not specified separately',
        )

        parser.add_argument(
            '--precision',
            type=int,
            default=DEFAULT_PRECISION,
            help='Precision for floating point comparisons. '
            'Two floats a and b will be '
            'considered equal if abs(a - b) < 1e-n,'
            'where n is the specified precision',
        )

        parser.add_argument(
            '--find-md',
            dest='find_md_flag',
            action='store_true',
            help='Attempt to find associated metadata for flat files.',
        )

        parser.add_argument(
            '--no-md',
            '--no-find-md',
            action='store_true',
            help='Do not attempt to find associated metadata for flat files.',
        )

        parser.add_argument(
            '--maxdiffs',
            type=int,
            default=None,
            help='Maximum number of differences to show.',
        )

        parser.add_argument(
            '--mono',
            action='store_true',
            help='Show monochrome output.',
        )

        parser.add_argument(
            '--bw',
            action='store_true',
            help='Show black and white output.',
        )

        parser.add_argument(
            '--AE',
            action='store_true',
            help='Use A: and E: as labels for the two datasets',
        )

        parser.add_argument(
            '--LR',
            action='store_true',
            help='Use L: and R: as labels for the two datasets',
        )

        parser.add_argument(
            '--angles',
            action='store_true',
            help='Use < and > as labels for the two datasets',
        )

        parser.add_argument(
            '--pm',
            action='store_true',
            help='Use + and - as labels for the two datasets',
        )

        parser.add_argument(
            '--prefixes',
            type=str,
            action='store',
            help='Use prefixes specified as labels for the two datasets, '
            'e.g. --prefixes "actual:-ref:"',
        )

        parser.add_argument(
            '--colours',
            '-c',
            '--colours',
            type=str,
            action='store',
            help='Use colours specified e.g. -c red-blue',
        )

        parser.add_argument(
            '--horizontal',
            '-H',
            action='store_true',
            help='Force horizontal dispay',
        )

        parser.add_argument(
            '--vertical',
            '-V',
            action='store_true',
            help='Force vertical dispay',
        )

        parser.add_argument(
            '--fields',
            type=str,
            action='store',
            help='Check only these fields (comma-separated list)',
        )

        parser.add_argument(
            '--xfields',
            type=str,
            action='store',
            help='Check all fields except these (comma-separated list)',
        )

        parser.add_argument(
            '--key',
            type=str,
            action='store',
            help='Use these fields as join key (comma-separated list); OPTIONAL',
        )

        parser.add_argument(
            '-N', '--no-config',
            action='store_true',
            help='Use default configuration (ignore ~/.tdda.toml)',
        )

        parser.add_argument(
            '--strict', action='store_true', help='Use strict type comparisons'
        )

        parser.add_argument(
            '--medium', action='store_true', help='Use medium type comparisons'
        )

        parser.add_argument(
            '--loose',
            action='store_true',
            help='Use loose (permissive) type comparisons',
        )

        parser.add_argument(
            '--permissive',
            action='store_true',
            help='Use loose (permissive) type comparisons',
        )
        add_pandas_flags(parser)
        return parser


def ddiff_helper(args, config=None, console=None):
    no_config = config is None and (
        '-N' in args or '--no-config' in args
    )
    config = get_config(config, force_no_global=no_config)
    tddadiff = TDDADiff(config, cli_args=args, console=console)
    try:
        if tddadiff.ddiff():
            sys.exit(1)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    ddiff_helper(sys.argv)
