# -*- coding: utf-8 -*-
#
# Example of a very simple constraint extension module.
#
# Extension modules are used to extend TDDA Discovery and Verification
# to other data stores/types etc. --- so there are 'extensions' for
# Pandas DataFrames and various databases (PostgreSQL, MySQL, SQLite and
# MongoDB) included with the TDDA library.
#
# This file illustrates how to build a simple extension, treating the
# file system as a data source and metadata about the files (name, size)
# as the 'fields' to be checked in a directory (which takes the place
# of a table or dataset).
#
# It doesn't implement any of the option flags for discovery or verification
# that it ought to.
#
# USAGE:
#
# To use this, you need to set the environment variable TDDA_EXTENSIONS
# to include the fully-qualified class defined in here with a command.
# If you have stored this in /home/ann/bar/files_extension.py, use
#
#  export TDDA_EXTENSIONS=bar.files_extension.TDDAFilesExtension
#
# and make your PYTHONPATH is such that this is importable (i.e. that the
# PYTHONPATH includes /home/ann in this case). You can check this by trying
#
#     from bar.files_extension import TDDAFilesExtension
#
# in a Python REPL.
#

from __future__ import print_function

import os
import re
import sys

from tdda.constraints.extension import ExtensionBase

from tdda.constraints.base import (
    DatasetConstraints,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintVerifier,
    BaseConstraintDiscoverer,
)
from tdda.rexpy import rexpy


class TDDAFilesExtension(ExtensionBase):
    def __init__(self, argv, verbose=False):
        ExtensionBase.__init__(self, argv, verbose=verbose)

    def applicable(self):
        return any(os.path.isdir(a) for a in self.argv)

    def help(self, stream=sys.stdout):
        print('  - Filesystem directories', file=stream)

    def spec(self):
        return 'a directory or folder'

    def discover(self):
        inc_rex = True
        path = self.argv[1]
        constraints_path = self.argv[2] if len(self.argv) > 2 else None
        disco = FilesConstraintDiscoverer(path, inc_rex=inc_rex)
        constraints = disco.discover()
        if constraints_path:
            with open(constraints_path, 'w') as f:
                f.write(constraints.to_json())
        else:
            print(constraints.to_json())

    def verify(self):
        path = self.argv[1]
        constraints_path = self.argv[2]
        epsilon = 0
        type_checking = 'strict'
        fv = FilesConstraintVerifier(path, epsilon=epsilon,
                                     type_checking=type_checking)
        constraints = DatasetConstraints(loadpath=constraints_path)
        print(fv.verify(constraints))


class FilesConstraintCalculator(BaseConstraintCalculator):
    def __init__(self, path):
        self.path = path

    def get_column_names(self):
        return ['name', 'size']

    def get_nrecords(self):
        return len(os.listdir(self.path))

    def types_compatible(self, x, y, colname):
        return type(x) == type(y)

    def calc_min(self, colname):
        names = os.listdir(self.path)
        vals = (names if colname == 'name'
                else [os.path.getsize(f) for f in names])
        return min(vals)

    def calc_max(self, colname):
        names = os.listdir(self.path)
        vals = (names if colname == 'name'
                else [os.path.getsize(f) for f in names])
        return max(vals)

    def calc_min_length(self, colname):
        assert colname == 'name'
        names = os.listdir(self.path)
        return min([len(f) for f in names])

    def calc_max_length(self, colname):
        assert colname == 'name'
        names = os.listdir(self.path)
        return max([len(f) for f in names])

    def calc_tdda_type(self, colname):
        return 'string' if colname == 'name' else 'int'

    def calc_null_count(self, colname):
        return 0

    def calc_non_null_count(self, colname):
        return len(os.listdir(self.path))

    def calc_nunique(self, colname):
        names = os.listdir(self.path)
        vals = (names if colname == 'name'
                else [os.path.getsize(f) for f in names])
        uniques = set(vals)
        return len(uniques)

    def calc_unique_values(self, colname, include_nulls=True):
        names = os.listdir(self.path)
        vals = (names if colname == 'name'
                else [os.path.getsize(f) for f in names])
        uniques = set(vals)
        return list(uniques)

    def calc_non_integer_values_count(self, colname):
        raise Exception('files should not require non_integer_values_count')

    def calc_all_non_nulls_boolean(self, colname):
        raise Exception('files should not require all_non_nulls_boolean')

    def find_rexes(self, colname, values=None):
        assert colname == 'name'
        if not values:
            values = calc_unique_values(colname)
        return rexpy.extract(values)

    def verify_rex_constraint(self, colname, constraint):
        names = os.listdir(self.path)
        for f in names:
            for r in constraint.value:
                if re.match(r, f) is not None:
                    break
            else:
                return False
        return True


class FilesConstraintDiscoverer(FilesConstraintCalculator,
                                BaseConstraintDiscoverer):
    def __init__(self, path, inc_rex=False):
        FilesConstraintCalculator.__init__(self, path)
        BaseConstraintDiscoverer.__init__(self, inc_rex=inc_rex)


class FilesConstraintVerifier(FilesConstraintCalculator,
                              BaseConstraintVerifier):
    def __init__(self, path, epsilon=None, type_checking='strict'):
        FilesConstraintCalculator.__init__(self, path)
        BaseConstraintVerifier.__init__(self, epsilon=epsilon,
                                        type_checking=type_checking)


