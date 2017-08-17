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

from tdda.constraints.flags import discover_parser, discover_flags
from tdda.constraints.flags import verify_parser, verify_flags
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
        parser = discover_parser()
        parser.add_argument('directory', nargs=1, help='directory path')
        parser.add_argument('constraints', nargs='?',
                            help='name of constraints file to create')
        params = {}
        flags = discover_flags(parser, self.argv[1:], params)
        params['path'] = flags.directory[0] if flags.directory else None
        params['constraints_path'] = (flags.constraints if flags.constraints
                                      else None)
        constraints = discover_directory(**params)
        results = constraints.to_json()
        if params['constraints_path']:
            with open(params['constraints_path'], 'w') as f:
                f.write(results)
        else:
            print(results)

    def verify(self):
        parser = verify_parser()
        parser.add_argument('directory', nargs=1, help='directory path')
        parser.add_argument('constraints', nargs=1,
                            help='constraints file to verify against')
        params = {}
        flags = verify_flags(parser, self.argv[1:], params)
        params['path'] = flags.directory[0] if flags.directory else None
        params['constraints_path'] = (flags.constraints[0] if flags.constraints
                                      else None)
        params['type_checking'] = 'strict'
        print(verify_directory_from_file(**params))


def discover_directory(path, constraints_path=None, **kwargs):
    disco = FilesConstraintDiscoverer(path, **kwargs)
    return disco.discover()


def verify_directory_from_file(path, constraints_path, **kwargs):
    fv = FilesConstraintVerifier(path, **kwargs)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return fv.verify(constraints)


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
    def __init__(self, path, **kwargs):
        FilesConstraintCalculator.__init__(self, path)
        BaseConstraintDiscoverer.__init__(self, **kwargs)


class FilesConstraintVerifier(FilesConstraintCalculator,
                              BaseConstraintVerifier):
    def __init__(self, path, type_checking='strict', **kwargs):
        FilesConstraintCalculator.__init__(self, path)
        BaseConstraintVerifier.__init__(self, type_checking=type_checking,
                                        **kwargs)


