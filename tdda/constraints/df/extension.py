# -*- coding: utf-8 -*-

"""
Extensions to the ``tdda`` command line tool, to support Pandas dataframes
and CSV files.
"""

import os
import sys

from tdda.constraints.extension import ExtensionBase

from tdda.constraints.df.discover import DFDiscoverer
from tdda.constraints.df.verify import DFVerifier
from tdda.constraints.df.detect import DFDetector

from tdda.utils import tdda_path_info


class TDDADFExtension(ExtensionBase):
    def __init__(self, argv, verbose=False):
        ExtensionBase.__init__(self, argv, verbose=verbose)

    def applicable(self):
        for a in self.argv:
            if a == '-':
                return True
            info = tdda_path_info(a)
            if info.ext in (
                '.csv',
                '.psv',
                '.tsv',
                '.parquet',
                '.json',
                '.yaml',
            ):
                return True
        return False

    def help(self, stream=sys.stdout):
        print('  - Flat files (filename.csv)', file=stream)
        print('  - Pandas DataFrames (filename.parquet)', file=stream)

    def spec(self):
        return 'a CSV file or a .parquet file'

    def discover(self):
        return DFDiscoverer(self.argv, verbose=self.verbose).discover()

    def verify(self):
        return DFVerifier(self.argv, verbose=self.verbose).verify()

    def detect(self):
        return DFDetector(self.argv, verbose=self.verbose).detect()
