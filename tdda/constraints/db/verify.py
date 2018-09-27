# -*- coding: utf-8 -*-

"""
Support for database constraint verification from the command-line tool
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

'''

import argparse
import os
import sys

from tdda import __version__
from tdda.constraints.flags import verify_parser, verify_flags
from tdda.constraints.db.constraints import verify_db_table
from tdda.constraints.db.drivers import (database_connection, parse_table_name,
                                         database_arg_parser,
                                         database_arg_flags)


def verify_database_table_from_file(table, constraints_path,
                                    conn=None, dbtype=None, db=None,
                                    host=None, port=None, user=None,
                                    password=None, **kwargs):
    """
    Verify the given database table, against constraints in the .tdda
    file specified.

    Prints results to stdout.
    """
    (table, dbtype) = parse_table_name(table, dbtype)
    db = database_connection(table=table, conn=conn, dbtype=dbtype, db=db,
                             host=host, port=port,
                             user=user, password=password)
    print(verify_db_table(dbtype, db, table, constraints_path, **kwargs))


def get_verify_params(args):
    parser = database_arg_parser(verify_parser, USAGE)
    parser.add_argument('table', nargs=1, help='database table name')
    parser.add_argument('constraints', nargs='?',
                        help='constraints file to verify against')
    params = {}
    flags = database_arg_flags(verify_flags, parser, args, params)
    params['table'] = flags.table[0] if flags.table else None
    params['constraints_path'] = flags.constraints
    return params


class DatabaseVerifier:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def verify(self):
        params = get_verify_params(self.argv[1:])
        verify_database_table_from_file(**params)


def main(argv):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    v = DatabaseVerifier(argv)
    v.verify()


if __name__ == '__main__':
    main(sys.argv)

