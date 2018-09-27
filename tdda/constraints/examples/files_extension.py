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
#
# If this file is stored as /home/ann/constraints_examples/files_extension.py,
# use
#
#  export TDDA_EXTENSIONS=constraints_examples.files_extension.TDDAFilesExtension
#
# and make your PYTHONPATH is such that this is importable (i.e. that the
# PYTHONPATH includes /home/ann in this case). You can check this by trying
#
#     from constraints_examples.files_extension import TDDAFilesExtension
#
# in a Python REPL.
#
# With TDDA_EXTENSIONS and PYTHONPATH set appropriately, the "tdda" command
# should now include this extension for using constraints on filesystem
# directories.
#
# To generate a set of constraints in the current directory, and put the
# generated constraints into a file in /tmp, use:
#
#   tdda discover . /tmp/directoryconstraints.tdda
#
# To verify some other directory against those constraints, use:
#
#   tdda verify some_other_directory /tmp/directoryconstraints.tdda
#
# To detect files that do not conform to the constraints, as a CSV file, use:
#
#   tdda detect some_other_directory /tmp/directoryconstraints.tdda bad.csv
#

from __future__ import print_function

import csv
import os
import re
import sys
from collections import OrderedDict

from tdda.constraints.flags import discover_parser, discover_flags
from tdda.constraints.flags import verify_parser, verify_flags
from tdda.constraints.flags import detect_parser, detect_flags
from tdda.constraints.extension import ExtensionBase

from tdda.constraints.base import (
    DatasetConstraints,
    Detection,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintVerifier,
    BaseConstraintDetector,
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
        params['constraints_path'] = flags.constraints
        constraints = discover_directory(**params)
        results = constraints.to_json()
        if params['constraints_path']:
            with open(params['constraints_path'], 'w') as f:
                f.write(results)
        else:
            print(results)
        return results

    def verify(self):
        parser = verify_parser()
        parser.add_argument('directory', nargs=1, help='directory path')
        parser.add_argument('constraints', nargs=1,
                            help='constraints file to verify against')
        return self.verify_or_detect(parser, detect=False)

    def detect(self):
        parser = detect_parser()
        parser.add_argument('directory', nargs=1, help='directory path')
        parser.add_argument('constraints', nargs=1,
                            help='constraints file to verify against')
        parser.add_argument('outpath', nargs='?',
                            help='file to write detected records to')
        return self.verify_or_detect(parser, detect=True)

    def verify_or_detect(self, parser, detect=False):
        params = {}
        if detect:
            flags = detect_flags(parser, self.argv[1:], params)
        else:
            flags = verify_flags(parser, self.argv[1:], params)
        params['path'] = flags.directory[0] if flags.directory else None
        params['constraints_path'] = (flags.constraints[0] if flags.constraints
                                      else None)
        if detect:
            params['outpath'] = flags.outpath
            results = detect_directory_from_file(**params)
        else:
            results = verify_directory_from_file(**params)

        if self.verbose:
            print(results)
        return results


def discover_directory(path, constraints_path=None, **kwargs):
    disco = FilesConstraintDiscoverer(path, **kwargs)
    return disco.discover()


def verify_directory_from_file(path, constraints_path, **kwargs):
    fv = FilesConstraintVerifier(path, **kwargs)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return fv.verify(constraints, **kwargs)


def detect_directory_from_file(path, constraints_path, **kwargs):
    fv = FilesConstraintVerifier(path, **kwargs)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return fv.detect(constraints, **kwargs)


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
                else [os.path.getsize(self.fullpath(f)) for f in names])
        return min(vals)

    def calc_max(self, colname):
        names = os.listdir(self.path)
        vals = (names if colname == 'name'
                else [os.path.getsize(self.fullpath(f)) for f in names])
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
                else [os.path.getsize(self.fullpath(f)) for f in names])
        uniques = set(vals)
        return len(uniques)

    def calc_unique_values(self, colname, include_nulls=True):
        names = os.listdir(self.path)
        vals = (names if colname == 'name'
                else [os.path.getsize(self.fullpath(f)) for f in names])
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

    def calc_rex_constraint(self, colname, constraint, detect=False):
        # note that this should return violations, so None means success
        assert colname == 'name'
        names = os.listdir(self.path)
        for f in names:
            for r in constraint.value:
                if re.match(r, f) is not None:
                    break
            else:
                return True
        return None   # should really return a Detection object

    def fullpath(self, f):
        return os.path.join(self.path, f)


class FilesConstraintDetector(BaseConstraintDetector):
    def __init__(self, path):
        self.path = path
        self.names = os.listdir(self.path)
        self.sizes = [os.path.getsize(self.fullpath(f)) for f in self.names]
        self.min_ok = {}
        self.max_ok = {}
        self.min_length_ok = {}
        self.max_length_ok = {}
        self.no_dups_ok = {}
        self.values_ok = {}
        self.rex_ok = {}

    def detect_min_constraint(self, colname, value, precision, epsilon):
        vals = self.names if colname == 'name' else self.sizes
        self.min_ok[colname] = [v >= value for v in vals]

    def detect_max_constraint(self, colname, value, precision, epsilon):
        vals = self.names if colname == 'name' else self.sizes
        self.max_ok[colname] = [v <= value for v in vals]

    def detect_min_length_constraint(self, colname, value):
        assert colname == 'name'
        self.min_length_ok[colname] = [len(v) >= value for v in self.names]

    def detect_max_length_constraint(self, colname, value):
        assert colname == 'name'
        self.max_length_ok[colname] = [len(v) <= value for v in self.names]

    def detect_no_duplicates_constraint(self, colname, value):
        vals = self.names if colname == 'name' else self.sizes
        multiplicity = [len([c for c in vals if c == v]) for v in vals]
        self.no_dups_ok[colname] = [m <= value
                                    for m in multiplicity]

    def detect_allowed_values_constraint(self, colname, allowed_values,
                                         violations):
        vals = self.names if colname == 'name' else self.sizes
        self.values_ok[colname] = [v not in violations for v in vals]

    def detect_rex_constraint(self, colname, violations):
        assert colname == 'name'
        self.rex_ok[colname] = [v not in violations for v in vals]

    def write_detected_records(self,
                               detect_outpath=None,
                               detect_write_all=False,
                               detect_per_constraint=False,
                               detect_output_fields=None,
                               detect_index=False,
                               detect_in_place=False,
                               **kwargs):
        input_fields = ['name', 'size']
        if detect_outpath:
            if detect_output_fields is None:
                detect_output_fields = input_fields
            else:
                for k in detect_output_fields:
                    if k not in ('name', 'size'):
                        raise Exception('Unknown column %s' % k)
            cnames = ('min', 'max', 'min_length', 'max_length',
                      'no_dups', 'values', 'rex')
            cvalues = (self.min_ok, self.max_ok, self.min_length_ok,
                       self.max_length_ok, self.no_dups_ok,
                       self.values_ok, self.rex_ok)
            ok_output_names = ['%s_%s_ok' % (fname, cname)
                               for fname in input_fields
                               for cname, v in zip(cnames, cvalues)
                                   if fname in v]
            bad_output_names = []
            if len(detect_output_fields) == 0:
                bad_output_names.append('RowNumber')
            for k in detect_output_fields:
                bad_output_names.append(k)
            for k in ok_output_names:
                bad_output_names.append(k)

            with open(detect_outpath, 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=bad_output_names)
                writer.writeheader()
                for i, (name, size) in enumerate(zip(self.names, self.sizes)):
                    record = OrderedDict()
                    if len(detect_output_fields) == 0:
                        record['RowNumber'] = i + 1
                    for k in detect_output_fields:
                        record[k] = name if k == 'name' else size
                    bad = False
                    for field in input_fields:
                        for constraint, ok in (zip(cnames, cvalues)):
                            if field in ok:
                                ok_field_name = '%s_%s_ok' % (field, constraint)
                                record[ok_field_name] = ok[field][i]
                                if ok[field][i] is False:
                                    bad = True
                    if bad or detect_write_all:
                        writer.writerow(record)
        return None

    def fullpath(self, f):
        return os.path.join(self.path, f)


class FilesConstraintDiscoverer(FilesConstraintCalculator,
                                BaseConstraintDiscoverer):
    def __init__(self, path, **kwargs):
        FilesConstraintCalculator.__init__(self, path)
        BaseConstraintDiscoverer.__init__(self, **kwargs)


class FilesConstraintVerifier(FilesConstraintCalculator,
                              FilesConstraintDetector,
                              BaseConstraintVerifier):
    def __init__(self, path, **kwargs):
        FilesConstraintCalculator.__init__(self, path)
        FilesConstraintDetector.__init__(self, path)
        BaseConstraintVerifier.__init__(self, **kwargs)


