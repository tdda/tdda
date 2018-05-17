# -*- coding: utf-8 -*-

"""
Support for database constraint detection from the command-line tool
"""

from __future__ import division
from __future__ import print_function

USAGE = '''

Parameters:

  * table is one of:

     - a database table name
     - a schema-qualified table name of the form schema.table
     - a database table name qualified by database type, of the
       form dbtype:table or dbtype:schema.table

  * constraints.tdda is a JSON .tdda file constaining constraints.

  * detection output file is not implemented yet.

'''

import argparse
import os
import sys

from tdda import __version__
from tdda.constraints.flags import detect_parser, detect_flags
from tdda.constraints.db.constraints import detect_db_table
from tdda.constraints.db.drivers import (database_connection, parse_table_name,
                                         database_arg_parser,
                                         database_arg_flags)


def detect_database_table_from_file(table, constraints_path,
                                    conn=None, dbtype=None, db=None,
                                    host=None, port=None, user=None,
                                    password=None, **kwargs):
    """
    detect using the given database table, against constraints in the .tdda
    file specified.

    Not implemented
    """
    (table, dbtype) = parse_table_name(table, dbtype)
    db = database_connection(table=table, conn=conn, dbtype=dbtype, db=db,
                             host=host, port=port,
                             user=user, password=password)
    print(detect_db_table(dbtype, db, table, constraints_path, **kwargs))


def get_detect_params(args):
    parser = database_arg_parser(detect_parser, USAGE)
    parser.add_argument('table', nargs=1, help='database table name')
    parser.add_argument('constraints', nargs=1,
                        help='constraints file to verify against')
    parser.add_argument('outpath', nargs='?',
                        help='file to write detection results to')
    params = {}
    flags = database_arg_flags(detect_flags, parser, args, params)
    params['table'] = flags.table[0] if flags.table else None
    params['constraints_path'] = (flags.constraints[0] if flags.constraints
                                  else None)
    params['outpath'] = flags.outpath
    return params


class DatabaseDetector:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def detect(self):
        params = get_detect_params(self.argv[1:])
        detect_database_table_from_file(**params)


def main(argv):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    v = DatabaseDetector(argv)
    v.detect()


if __name__ == '__main__':
    main(sys.argv)

