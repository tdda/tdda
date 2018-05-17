# -*- coding: utf-8 -*-

"""
Extensions to the ``tdda`` command line tool, to support Pandas dataframes
and CSV files.
"""

from __future__ import print_function

import sys

from tdda.constraints.extension import ExtensionBase

from tdda.constraints.pd.discover import PandasDiscoverer
from tdda.constraints.pd.verify import PandasVerifier
from tdda.constraints.pd.detect import PandasDetector


class TDDAPandasExtension(ExtensionBase):
    def __init__(self, argv, verbose=False):
        ExtensionBase.__init__(self, argv, verbose=verbose)

    def applicable(self):
        for a in self.argv:
            if a.endswith('.csv') or a.endswith('.feather') or a == '-':
                return True
        return False

    def help(self, stream=sys.stdout):
        print('  - Flat files (filename.csv)', file=stream)
        print('  - Pandas DataFrames (filename.feather)', file=stream)

    def spec(self):
        return 'a CSV file or a .feather file'

    def discover(self):
        return PandasDiscoverer(self.argv, verbose=self.verbose).discover()

    def verify(self):
        return PandasVerifier(self.argv, verbose=self.verbose).verify()

    def detect(self):
        return PandasDetector(self.argv, verbose=self.verbose).detect()

