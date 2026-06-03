import argparse
import os
import sys

from tdda.state import get_config

from tdda.serial.csvw import serial_to_csvw
from tdda.serial.frictionless import serial_to_frictionless
from tdda.serial.infer import infer_format_from_flat_file
from tdda.serial.metadata import SerialMetadata, get_metadata_flavours
from tdda.serial.pandasio import (
    serial_to_pandas_read_csv_args,
    serial_to_pandas_write_csv_args,
    serial_to_pandas_read_csv_python,
)
from tdda.serial.polarsio import (
    serial_to_polars_read_csv_args,
    serial_to_polars_read_csv_python,
    serial_to_polars_write_csv_args,
)
from tdda.serial.reader import load_metadata
from tdda.serial.utils import find_metadata_type_from_path
from tdda.utils import error, warn, nvl


UNSUPPORTED_FMT_MSG = """
You have requested %s.
This is not yet implemented.

There is fairly comprehensive support in tdda.serial for:

  tdda.serial
  pd.r  (pandas.read_csv)
  pd.w  (pandas.DataFrame.to_csv)
  pl.r  (polars.read_csv)
  CSVW  (CSV on the Web, where it overlaps)
  Frictionless packages and resources
         (schemas to follow)

The Pandas support includes dtype backends:
  o  (original)
  n  (numpy_nullable)
  a  (Apache PyArrow)

Next planned is pl.w (polars.DataFrame.write_csv),
which currently has only partial support,
followed by Python csv module and then native PyArrow.

DuckDB and Excel will probably follow later.
""".lstrip()


CONVERTER = {
    'pandas.read_csv': serial_to_pandas_read_csv_args,
    'pandas.DataFrame.to_csv': serial_to_pandas_write_csv_args,
    'polars.read_csv': serial_to_polars_read_csv_args,
    'polars.DataFrame.write_csv': serial_to_polars_write_csv_args,
}


PYTHON_WRITER = {
    'pandas.read_csv': serial_to_pandas_read_csv_python,
    'polars.read_csv': serial_to_polars_read_csv_python,
}

USAGE = """
tdda serial [FLAGS] INPATH OUTPUT

  INPATH     A source metadata file or a flat file for metadata generation

             The extension partly determines the format:
                .serial                 --- tdda.serial
                .yaml                   --- Frictionless
                .json                   --- CSVW or Frictionless
                .csv, .psv, .tsv, .txt  --- flat file input for generation

  OUTPUT        Can be either another metadata file, with an extention
                as above, or a .py file for a stand-alone
                Python script to be generated.

FLAGS:

  --to TO  Destination format/flavour specifer.

           TO                          FORMAT and FLAVOUR
           --------------------------  ---------------------
           tdda.serial                 tdda.serial (default)
           .                           tdda.serial

           pandas.read_csv             pandas.read_csv (tdda.serial)
           pd.r                        pandas.read_csv (tdda.serial)

           pandas.DataFrame.to_csv     pandas.DataFrame.to_csv (tdda.serial)
           pd.w                        pandas.DataFrame.to_csv (tdda.serial)

           polars.read_csv             polars.read_csv (tdda.serial)
           pl.r                        polars.read_csv (tdda.serial)

           polars.DataFrame.write_csv  polars.DataFrame.write_csv (tdda.serial)
           pl.w                        polars.DataFrame.write_csv (tdda.serial)

           csvw                        CSVW

           frictionless                Frictionless
           fless                       Frictionless
           fl                          Frictionless
           fl.r                        Frictionless resource
           fl.p                        Frictionless package


  --for FILE    Filename for data to use when generating CSVW or Frictionless
                data. (Can also be used for tdda.serial and .py output)

  --backend BE, -B BE  Backend target dtypes when writing pandas flavours
                       n for numpy_nullable, a for pyarrow, o for original

  --generate, --gen, -g

  --verbose, -v  Verbose
  --Verbose, -V  More verbose
"""


class SerialConverter:
    def __init__(
        self,
        inpath=None,
        outpath=None,
        out_format=None,
        backend=None,
        map_other_bools_to_string=False,
        generate=False,
        cli_args=None,
        single_field=None,
        for_csv=None,
        config=None,
        verbosity=None,
    ):
        self.inpath = inpath
        self.outpath = outpath
        self.cli_args = cli_args
        self._out_format = out_format
        self.verbosity = nvl(verbosity, 1)
        self.sconfig = get_config(config).serial
        self.for_csv = for_csv
        self.backend = backend
        self.generate = generate
        self.single_field = single_field
        self.map_other_bools_to_string = map_other_bools_to_string
        if self.cli_args is not None:
            self.process_args()
        self.validate()

    def process_args(self):
        parser = self.parser()
        # flags, more = parser.parse_known_args(self.cli_args)
        flags = parser.parse_args(self.cli_args)
        if flags.verbose or flags.Verbose:
            flags.verbosity = 3 if flags.Verbose else 2
        if flags.quiet:
            flags.verbosity = 0
        flags._out_format = getattr(flags, 'to', None)
        flags.for_csv = getattr(flags, 'for', None)
        flags.single_field = getattr(flags, 'single', None)
        self.__dict__.update(vars(flags))

    def validate(self):
        if not self.outpath:
            suf = USAGE if self.cli_args else None
            error(f'No destination specified.{suf}')

        fmt = self._out_format or []
        if fmt:
            self.out_formats = get_metadata_flavours(fmt)  # standardize
        else:
            self.out_formats = []
        if self.out_formats:
            kind = self.out_formats[0]
        else:
            kind, parts = find_metadata_type_from_path(self.outpath)
            self.out_formats = [kind]
        _, ext = os.path.splitext(self.outpath)
        ext = ext

        if 'csvw' in self.out_formats and len(self.out_formats) > 1:
            error('You cannot combine csvw with other output formats.')
        if len(self.out_formats) > 1 and (
            'frictionless' in self.out_formats
            or 'frictionless.resource' in self.out_formats
            or 'frictionless.package' in self.out_formats
        ):
            error('You cannot combine frictionless with other output formats.')

        if ext == '.py':
            self.broad_out = 'python'
        elif ext == '.serial':
            self.broad_out = 'tdda.serial'
        elif kind:
            self.broad_out = kind
        elif ext in ('.csvw'):
            self.broad_out = 'csvw'
        else:
            error('Cannot infer output format. Use --to FMT to specify.')

        self.for_csv = nvl(self.for_csv, getattr(self, 'for', None))

        _, in_ext = os.path.splitext(self.inpath)
        is_flat_file = in_ext in ('.csv', '.psv', '.tsv', '.txt')
        if getattr(self, 'generate', False) or is_flat_file:
            self.generate = True

        if self.inpath == self.outpath:
            error('inpath and outpath cannot be the same.')

    def parser(self):
        formatter = argparse.RawDescriptionHelpFormatter
        parser = argparse.ArgumentParser(
            prog='tdda serial',
            # epilog=TDDA_DIFF_HELP,
            formatter_class=formatter,
        )

        parser.add_argument(
            'inpath',
            help='input file (.serial, csvw (json), '
            'frictionless (yaml/json) or flat file (.csv, .psv etc.)',
        )
        parser.add_argument(
            'outpath', nargs='?', help='output metadata file or python script'
        )

        parser.add_argument(
            '-?', '--?', action='help', help='same as -h or --help'
        )

        parser.add_argument(
            '--to',
            type=str,
            help='output format or formats (comma separated for multiple).',
        )

        parser.add_argument(
            '--for',
            type=str,
            help='csv file to use as url in written metadata',
        )

        parser.add_argument(
            '--backend',
            '-B',
            type=str,
            help='For Pandas, preferred backend.'
            ' n (or numpy_nullable),'
            ' a (or pyarrow),'
            ' o (or original).',
        )

        parser.add_argument(
            '--generate',
            '--gen',
            '-g',
            action='store_true',
            help='Generate an inferred tdda.serial file for a CSV file provided',
        )

        parser.add_argument(
            '--sep',
            '--delimiter',
            type=str,
            dest='delimiter',
            help='Specify inferred field delimiter.',
        )
        parser.add_argument(
            '--quote-char',
            '--quote',
            type=str,
            dest='quote_char',
            help='Specify quote character.',
        )
        parser.add_argument(
            '--escape',
            action='store_true',
            help='Use \\ as escape character.',
        )
        parser.add_argument(
            '--no-escape',
            action='store_true',
            dest='no_escape',
            help='Force no escape character.',
        )
        parser.add_argument(
            '--stutter',
            action='store_true',
            default=None,
            help='Specify stutter (doubled) quote style.',
        )
        parser.add_argument(
            '--no-stutter',
            action='store_false',
            dest='stutter',
            help='Specify no stutter quote style.',
        )
        parser.add_argument(
            '--quoting',
            type=str,
            help='Specify quoting style'
            ' (QUOTE_ALL, QUOTE_MINIMAL, QUOTE_NONNUMERIC,'
            ' QUOTE_NONE, QUOTE_NOTNULL, QUOTE_STRINGS,'
            ' QUOTE_STRINGS_ONLY).',
        )
        parser.add_argument(
            '--nulls',
            type=str,
            help='Specify null indicator or comma-separated null indicators.',
        )
        parser.add_argument(
            '-e',
            '--encoding',
            type=str,
            help='Specify inferred encoding.',
        )
        parser.add_argument(
            '-n',
            '--sample-lines',
            type=int,
            dest='lines_to_use',
            help='Number of data lines to sample for inference.',
        )
        parser.add_argument(
            '--date-format',
            type=str,
            dest='date_format',
            help='Specify date format.',
        )
        parser.add_argument(
            '--datetime-format',
            type=str,
            dest='datetime_format',
            help='Specify datetime format.',
        )
        parser.add_argument(
            '--use-yyyy-dates',
            action='store_const',
            const='yyyy',
            dest='date_style',
            help='Write date formats in YYYY-style (e.g. DD/MM/YYYY).',
        )
        parser.add_argument(
            '--use-literal-dates',
            action='store_const',
            const='literal',
            dest='date_style',
            help='Write date formats as literal strings (e.g. dd/mm/yyyy).',
        )
        parser.add_argument(
            '--use-pc-dates',
            action='store_const',
            const='percent',
            dest='date_style',
            help='Write date formats in %%-style (e.g. %%d/%%m/%%Y).',
        )
        parser.add_argument(
            '--quiet', '-q', action='store_true', help='Be quiet'
        )

        parser.add_argument(
            '--verbose', '-v', action='store_true', help='Be verbose'
        )

        parser.add_argument(
            '--Verbose', '-V', action='store_true', help='Be more verbose'
        )

        parser.add_argument(
            '--single-field',
            '--single',
            '-1',
            action='store_true',
            dest='single',
            help='Declare that there is only a single field in the file.',
        )

        parser.add_argument(
            '--include-path',
            action='store_true',
            default=None,
            dest='include_path',
            help='Include path to data file in .serial output.',
        )

        parser.add_argument(
            '--exclude-path',
            action='store_true',
            default=None,
            dest='exclude_path',
            help='Exclude path to data file from .serial output.',
        )

        parser.add_argument(
            '-N', '--no-config',
            action='store_true',
            help='Use default configuration (ignore ~/.tdda.toml)',
        )

        return parser

    def warn(self, *args, **kw):
        if self.verbosity > 0:
            warn(*args, **kw)

    def convert(self, debug=False, warner=None):
        Warn = nvl(warner, self.warn)
        if debug or self.verbosity > 2:
            print(f'IN: {self.inpath}')
            print(f'OUT: {self.outpath}')
            print(f'FORMAT: {self.out_formats}')
            print(f'BACKEND: {self.backend}')
            print(f'GENERATE: {self.generate}')

        if not self.generate:
            md_in = load_metadata(self.inpath, verbosity=self.verbosity)
        md_out = (
            md_in.copy_serial()
            if 'tdda.serial' in self.out_formats and not self.generate
            else SerialMetadata()
        )
        kw = {}
        if self.generate:
            md_out = self.infer_from_flat_file(warner=Warn)
            md_in = md_out
        for fmt in self.out_formats:
            if fmt == 'tdda.serial':
                pass
            elif fmt == 'csvw':
                pass
            elif fmt == 'frictionless':
                pass
            elif self.broad_out != 'python':
                convert = CONVERTER.get(fmt)
                if convert is None:
                    error(UNSUPPORTED_FMT_MSG % fmt)
                if not getattr(md_out, 'libs', None):
                    md_out.libs = {}
                if self.map_other_bools_to_string:
                    kw['map_other_bools_to_string'] = True
                md_out.libs[fmt] = convert(
                    md_in, backend=self.backend, warner=Warn, **kw
                )

        if self.broad_out == 'tdda.serial':
            if getattr(self, 'exclude_path', None):
                md_out.path = None
            elif getattr(self, 'include_path', None) or self.for_csv:
                md_out.path = (
                    self.for_csv
                    or getattr(md_in, 'path', None)
                    or (self.inpath if self.generate else None)
                )
            md_out.write(
                self.outpath,
                verbose=self.verbosity > 1,
                date_style=getattr(self, 'date_style', None),
            )
        elif self.broad_out == 'csvw':
            c = serial_to_csvw(md_in)
            c.write_csvw(self.outpath, self.for_csv)
        elif self.broad_out == 'frictionless':
            fless = serial_to_frictionless(md_in)
            fless.write_frictionless(self.outpath, self.for_csv)
        elif self.broad_out == 'python':
            with open(self.outpath, 'w', encoding='utf-8') as f:
                python_writer = PYTHON_WRITER.get(fmt)
                if python_writer is None:
                    error(
                        'Only pd.r (pandas.read_csv) and pl.r'
                        ' (polars.read_csv) are supported\n'
                        'for Python generation at this time.'
                    )
                f.write(
                    python_writer(
                        md_in, backend=self.backend, warner=Warn, **kw
                    )
                )
                if self.for_csv:
                    f.write(f'\ndf = read_data({self.for_csv!r})\n')
        else:
            Warn(f'Invalid broad output type: {self.broad_out}.')

    def infer_from_flat_file(self, warner=None):
        nulls = getattr(self, 'nulls', None)
        if nulls is not None:
            null = [n for n in nulls.split(',')]
            null = null[0] if len(null) == 1 else null
        else:
            null = None
        return infer_format_from_flat_file(
            self.inpath,
            single_field=self.single_field,
            verbosity=self.verbosity,
            lines_to_use=getattr(self, 'lines_to_use', None),
            delimiter=getattr(self, 'delimiter', None),
            quote_char=getattr(self, 'quote_char', None),
            escape='\\' if getattr(self, 'escape', None) else None,
            no_escape=getattr(self, 'no_escape', False),
            stutter=getattr(self, 'stutter', None),
            null=null,
            encoding=getattr(self, 'encoding', None),
            date_format=getattr(self, 'date_format', None),
            datetime_format=getattr(self, 'datetime_format', None),
            quoting=getattr(self, 'quoting', None),
            warner=warner,
        )


def serial_cli(args):
    converter = SerialConverter(cli_args=args)
    converter.convert()


if __name__ == '__main__':
    serial_cli(sys.argv)
