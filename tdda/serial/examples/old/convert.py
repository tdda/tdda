import os
import sys

from tdda.utils import error

from tdda.serial.metadata import SerialMetadata
from tdda.serial.reader import load_metadata
from tdda.serial.pandasio import pandas_read_csv_to_tddaserial

USAGE = 'USAGE: python convert.py in-metadata-path [out-metadata-path]'


def main(inpath, outpath=None):
    md_in = load_metadata(inpath)
    libs = md_in.libs
    pd_kw = libs.get('pandas.read_csv')
    if pd_kw:
        kw = pandas_read_csv_to_tddaserial(pd_kw)
        md_out = SerialMetadata(**kw)
        if outpath:
            with open(outpath, 'w') as f:
                f.write(md_out.to_json())
        else:
            print(md_out.to_json())


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        error(USAGE)
    main(*args)
