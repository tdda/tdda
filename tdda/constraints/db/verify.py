# -*- coding: utf-8 -*-

"""
Support for database constraint verification from the command-line tool
"""

from __future__ import division
from __future__ import print_function

USAGE = ''''
Verify CSV files, or Pandas or R DataFrames saved as feather files,
against a constraints from .tdda JSON file.
constraints file.

Usage:

    tdda verify [FLAGS] database-table constraints.tdda

where:

  * database-table is one of:

     - a database table name
     - a schema-qualified table name of the form schema.table
     - a database table name qualified by database type, of the
       form dbtype:table or dbtype:schema.table

  * constraints.tdda is a JSON .tdda file constaining constraints.

Optional flags are:

  * -a, --all
      Report all fields, even if there are no failures
  * -f, --fields
      Report only fields with failures
  * -c, --constraints
      Report only individual constraints that fail.  Not yet implemented.
  * -1, --oneperline
      Report each constraint failure on a separate line.  Not yet implemented.
  * -7, --ascii
      Report in ASCII form, without using special characters.
'''

import argparse
import os
import sys

from tdda import __version__
from tdda.constraints.db.constraints import verify_db_table
from tdda.constraints.db.drivers import (database_connection, parse_table_name,
                                         DATABASE_USAGE)


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


def get_params(args):
    params = {
        'table': None,
        'constraints_path': None,
        'report': 'all',
        'one_per_line': False,
        'ascii': False,
        'conn': None,
        'dbtype': None,
        'db': None,
        'host': None,
        'port': None,
        'user': None,
        'password': None,
    }
    parser = argparse.ArgumentParser(prog='tdda verify')
    parser.add_argument('-?', '--?', action='help',
                        help='same as -h or --help')
    parser.add_argument('-a', '--all', action='store_true',
                        help='report all fields, even if there are '
                             'no failures')
    parser.add_argument('-f', '--fields', action='store_true',
                        help='report only fields with failures')
    parser.add_argument('-c', '--constraints', action='store_true',
                        help='report only individual constraints that fail')
    parser.add_argument('-1', '--oneperline', action='store_true',
                        help='report each constraint failure on a '
                             'separate line')
    parser.add_argument('-7', '--ascii', action='store_true',
                        help='report without using special characters')
    parser.add_argument('-conn', '--conn', nargs=1,
                        help='database connection file')
    parser.add_argument('-dbtype', '--dbtype', nargs=1, help='database type')
    parser.add_argument('-db', '--db', nargs=1, help='database name')
    parser.add_argument('-host', '--host', nargs=1,
                        help='database server hostname')
    parser.add_argument('-port', '--port',
                        nargs=1, help='database server IP port')
    parser.add_argument('-user', '--user', nargs=1, help='username')
    parser.add_argument('-password', '--password', nargs=1, help='password')
    parser.add_argument('table', nargs=1, help='database table name')
    parser.add_argument('constraints', nargs=1,
                        help='constraints file to verify against')
    flags, more = parser.parse_known_args(args)

    if flags.all:
        params['report'] = 'all'
    elif flags.fields:
        params['report'] = 'fields'
    elif flags.constraints:
        params['report'] = 'constraints'
    if flags.oneperline:
        params['one_per_line'] = True
    if flags.ascii:
        params['ascii'] = True
    if flags.conn:
        params['conn'] = flags.conn[0]
    if flags.dbtype:
        params['dbtype'] = flags.dbtype[0]
    if flags.db:
        params['db'] = flags.db[0]
    if flags.host:
        params['host'] = flags.host[0]
    if flags.port:
        params['port'] = int(flags.port[0])
    if flags.user:
        params['user'] = flags.user[0]
    if flags.password:
        params['password'] = flags.password[0]
    params['table'] = flags.table[0] if flags.table else None
    params['constraints_path'] = (flags.constraints[0] if flags.constraints
                                  else None)
    if len(more) > 0:
        usage_error()
    return params


def usage_error():
    print(USAGE + DATABASE_USAGE, file=sys.stderr)
    sys.exit(1)


class DatabaseVerifier:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def verify(self):
        params = get_params(self.argv[1:])
        verify_database_table_from_file(**params)


def main(argv):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    v = DatabaseVerifier(argv)
    v.verify()


if __name__ == '__main__':
    main(sys.argv)

