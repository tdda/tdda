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
)
from tdda.serial.reader import load_metadata
from tdda.serial.utils import find_metadata_type_from_path
from tdda.utils import error, warn, nvl


CONVERTER = {
    'pandas.read_csv': serial_to_pandas_read_csv_args,
    'pandas.DataFrame.to_csv': serial_to_pandas_write_csv_args,
    'polars.read_csv': serial_to_polars_read_csv_args,
}


PYTHON_WRITER = {
    'pandas.read_csv': serial_to_pandas_read_csv_python,
    'polars.read_csv': serial_to_polars_read_csv_python,
}

USAGE = '''
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

  --backend BE, -b BE  Backend target dtypes when writing pandas flavours
                       n for numpy_nullable, a for pyarrow, o for original

  --generate, --gen, -g
'''



class SerialConverter:
    def __init__(self, inpath=None, outpath=None,
                 out_format=None, backend=None,
                 map_other_bools_to_string=False,
                 generate=False, cli_args=None,
                 for_csv=None, config=None):
        self.inpath = inpath
        self.outpath = outpath
        self.out_formats = self.handle_formats(out_format)
        self.backend = backend
        self.generate = generate
        self.cli_args = cli_args
        self.map_other_bools_to_string = map_other_bools_to_string
        self.sconfig = get_config().serial
        self.for_csv = for_csv
        if self.cli_args is not None:
            self.process_args()
        self.validate()

    def handle_formats(self, out_formats):
        fmt = out_formats or []
        if isinstance(fmt, str):
            fmt  = [fmt]
        return get_metadata_flavours(out_formats)  # standardize

    def process_args(self):
        parser = self.parser()
        flags, more = parser.parse_known_args(self.cli_args)
        self.__dict__.update(vars(flags))

    def validate(self):
        if not self.outpath:
            suf = USAGE if self.cli_args else None
            error(f'No destination specified.{suf}')
        kind, parts = find_metadata_type_from_path(self.outpath)
        _, ext = os.path.splitext(self.outpath)
        ext = ext
        if hasattr(self, 'to'):
            self.out_formats = get_metadata_flavours(self.to)

        if 'csvw' in self.out_formats and len(self.out_formats) > 1:
            error('You cannot combine csvw with other output formats.')
        if (
            len(self.out_formats) > 1
            and ('frictionless' in self.out_formats
                 or 'frictionless.resource' in self.out_formats
                 or 'frictionless.package' in self.out_formats)
        ):
            error('You cannot combine frictionless with other output formats.')

        if ext == '.py':
            self.broad_out = 'python'
        elif kind:
            self.broad_out = kind
        elif ext in ('.csvw'):
            self.broad_out = 'csvw'
        else:
            warn('Cannot infer output format. Use --to FMT to specify.')

        self.for_csv = getattr(self, 'for', None)

        _, in_ext = os.path.splitext(self.inpath)
        is_flat_file = in_ext in ('.csv', '.psv', '.tsv', '.txt')
        if getattr(self, 'generate', False) or is_flat_file:
            self.generate = True

        if self.inpath == self.outpath:
            error('inpath and outpath cannot be the same.')

    def parser(self):
        formatter = argparse.RawDescriptionHelpFormatter
        parser = argparse.ArgumentParser(prog='tdda serial',
                                         # epilog=TDDA_DIFF_HELP,
                                         formatter_class=formatter)

        parser.add_argument('inpath',
            help='input file (.serial, csvw (json), '
                 'frictionless (yaml/json) or flat file (.csv, .psv etc.)')
        parser.add_argument('outpath', nargs='?',
                            help='output metadata file or python script)')

        parser.add_argument('-?', '--?', action='help',
                            help='same as -h or --help')

        parser.add_argument('--to', type=str,
            help='output format or formats (comma separated for multiple).')

        parser.add_argument('--for', type=str,
            help='csv file to use as url in written metadata')

        parser.add_argument('--backend', '-B', type=str,
            help='For Pandas, preferred backend.'
                 ' n (or numpy_nullable),'
                 ' a (or pyarrow),'
                 ' o (or original).')

        parser.add_argument('--generate', '--gen', '-g', action='store_true',
            help='Generate a bare-bones tdda.serial file for a '
                 'CSV file provided')

        return parser

    def convert(self, debug=False, warner=None):
        Warn = nvl(warner, warn)
        if debug:
            print(f'IN: {self.inpath}')
            print(f'OUT: {self.outpath}')
            print(f'FORMAT: {self.out_formats}')
            print(f'BACKEND: {self.backend}')
            print(f'GENERATE: {self.generate}')

        if not self.generate:
            md_in = load_metadata(self.inpath)
        md_out = (
            md_in.copy_serial()
            if 'tdda.serial' in self.out_formats and not self.generate
            else SerialMetadata()
        )
        kw = {}
        for fmt in self.out_formats:
            if self.generate:
                md_out = self.infer_from_flat_file()
            elif fmt == 'tdda.serial':
                pass
            elif fmt == 'csvw':
                pass
            else:
                convert = CONVERTER[fmt]
                if not getattr(md_out, 'libs', None):
                    md_out.libs = {}
                if self.map_other_bools_to_string:
                    kw['map_other_bools_to_string'] = True
                md_out.libs[fmt] = convert(md_in, backend=self.backend,
                                           warner=Warn, **kw)

        if self.broad_out == 'tdda.serial':
            md_out.write(self.outpath)
        elif self.broad_out == 'csvw':
            csvw = serial_to_csvw(md_out)
            csvw.write_csvw(self.outpath, self.for_csv)
        elif self.broad_out == 'frictionless':
            fless = serial_to_frictionless(md_out)
            fless.write_frictionless(self.outpath, self.for_csv)
        elif self.broad_out == 'python':
            with open(self.outpath, 'w') as f:
                python_writer = PYTHON_WRITER.get(fmt)
                if python_writer is None:
                    error('No target library/format (e.g. pd.r) specified')
                f.write(python_writer(md_out, backend=self.backend,
                                      warner=Warn, **kw))
        else:
            Warn('Surprising to get here.')

    def infer_from_flat_file(self):
        return infer_format_from_flat_file(self.inpath)


def serial_cli(args):
    converter = SerialConverter(cli_args=args)
    converter.convert()


if __name__ == '__main__':
    serial_cli(sys.argv)
