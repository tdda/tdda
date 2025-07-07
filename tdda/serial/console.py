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
)
from tdda.utils import error, warn


CONVERTER = {
    'pandas.read_csv': serial_to_pandas_read_csv_args,
    'pandas.DataFrame.to_csv': serial_to_pandas_write_csv_args,
    'polars.read_csv': serial_to_polars_read_csv_args,
}


PYTHON_WRITER = {
    'pandas.read_csv': serial_to_pandas_read_csv_python,
}


class SerialConverter:
    def __init__(self, args, config=None):
        self.args = args
        self.sconfig = get_config().serial
        self.process_args()

    def process_args(self):
        parser = self.parser()
        flags, more = parser.parse_known_args(self.args)
        self.__dict__.update(vars(flags))

        _, ext = os.path.splitext(self.outpath)
        if ext == '.serial':
            self.broad_out = 'tdda.serial'
        elif ext in ('.json', '.csvw'):
            self.broad_out = 'csvw'
        elif ext == '.py':
            self.broad_out = 'python'
        else:
            warn('Non-standard output extension {ext}. Continuing.')

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

    def convert(self):
        print(f'IN: {self.inpath}')
        print(f'OUT: {self.outpath}')
        print(f'FORMAT: {self.out_formats}')
        print(f'BACKEND: {self.backend}')

        md_in = load_metadata(self.inpath)
        md_out = (
            md_in.copy_serial() if 'tdda.serial' in self.out_formats
            else SerialMetadata
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
                md_out.libs[fmt] = convert(md_in)

        if self.broad_out == 'tdda.serial':
            md_out.write(self.outpath)
        elif self.broad_out == 'csvw':
            #md_out.write(self.outpath)
            pass
        elif self.broad_out == 'python':
            with open(self.outpath, 'w') as f:
                python_writer = PYTHON_WRITER.get(fmt)
                f.write(python_writer(md_out, self.backend))
        else:
            warn('Surprising to get here.')


def serial_helper(args):
    converter = SerialConverter(args)
    converter.convert()


if __name__ == '__main__':
    serial_helper(sys.argv)
