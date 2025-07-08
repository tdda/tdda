import argparse
import os
import sys

from tdda.state import get_config

from tdda.serial.metadata import SerialMetadata, get_metadata_flavours
from tdda.serial.reader import load_metadata
from tdda.serial.pandasio import (
    serial_to_pandas_read_csv_args,
    serial_to_pandas_write_csv_args,
    serial_to_pandas_read_csv_python,
)
from tdda.serial.polarsio import (
    serial_to_polars_read_csv_args,
    serial_to_polars_read_csv_python,
)
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


class SerialConverter:
    def __init__(self, inpath=None, outpath=None,
                 out_format=None, backend=None,
                 cli_args=None, config=None):
        self.inpath = inpath
        self.outpath = outpath
        self.out_formats = self.handle_formats(out_format)
        self.backend = backend
        self.cli_args = cli_args
        self.sconfig = get_config().serial
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
        _, ext = os.path.splitext(self.outpath)
        if ext == '.serial':
            self.broad_out = 'tdda.serial'
        elif ext in ('.json', '.csvw'):
            self.broad_out = 'csvw'
        elif ext == '.py':
            self.broad_out = 'python'
        else:
            warn('Non-standard output extension {ext}. Continuing.')

        if hasattr(self, 'to'):
            self.out_formats = get_metadata_flavours(self.to)
        if 'csvw' in self.out_formats and len(self.out_formats) > 1:
            error('You cannot combine csvw with other output formats.')

    def parser(self):
        formatter = argparse.RawDescriptionHelpFormatter
        parser = argparse.ArgumentParser(prog='tdda serial',
                                         # epilog=TDDA_DIFF_HELP,
                                         formatter_class=formatter)

        parser.add_argument('inpath',
            help='input metadata file (.serial or csw')
        parser.add_argument('outpath', nargs='?',
                            help='output metadata file (if any)')

        parser.add_argument('-?', '--?', action='help',
                            help='same as -h or --help')

        parser.add_argument('--to', type=str,
            help='output format or formats (comma separated for multiple).')

        parser.add_argument('--backend', '-B', type=str,
            help='For Pandas, preferred backend.'
                 ' n or numpy_nullable,'
                 ' a or pyarrow,'
                 ' o or original')

        return parser

    def convert(self, debug=False, warner=None):
        Warn = nvl(warner, warn)
        if debug:
            print(f'IN: {self.inpath}')
            print(f'OUT: {self.outpath}')
            print(f'FORMAT: {self.out_formats}')
            print(f'BACKEND: {self.backend}')

        md_in = load_metadata(self.inpath)
        md_out = (
            md_in.copy_serial() if 'tdda.serial' in self.out_formats
            else SerialMetadata()
        )
        for fmt in self.out_formats:
            if fmt == 'tdda.serial':
                pass
            elif fmt == 'csvw':
                pass
            else:
                convert = CONVERTER[fmt]
                if not getattr(md_out, 'libs', None):
                    md_out.libs = {}
                md_out.libs[fmt] = convert(md_in, backend=self.backend,
                                           warner=Warn)

        if self.broad_out == 'tdda.serial':
            md_out.write(self.outpath)
        elif self.broad_out == 'csvw':
            #md_out.write(self.outpath)
            pass
        elif self.broad_out == 'python':
            with open(self.outpath, 'w') as f:
                python_writer = PYTHON_WRITER.get(fmt)
                f.write(python_writer(md_out, backend=self.backend,
                                      warner=Warn))
        else:
            Warn('Surprising to get here.')


def serial_cli(args):
    converter = SerialConverter(cli_args=args)
    converter.convert()


if __name__ == '__main__':
    serial_cli(sys.argv)
