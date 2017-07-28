# -*- coding: utf-8 -*-

"""
Support for database constraint discovery from the command-line tool
"""

from __future__ import division
from __future__ import print_function

USAGE = ''''
Discover TDDA constraints for database tables, and save the generated
constraints as a .tdda JSON file.

Usage:

    tdda discover [FLAGS] database-table [constraints.tdda]

where

  * database-table is one of:

     - a database table name
     - a schema-qualified table name of the form schema.table
     - a database table name qualified by database type, of the
       form dbtype:table or dbtype:schema.table

  * constraints.tdda, if provided, specifies the name of a file to
    which the generated constraints will be written.

  * supported flags are

     -r or --rex    to include regular expression generation
     -R or --norex  to exclude regular expression generation
'''

import argparse
import os
import sys

from tdda import __version__
from tdda.constraints.db.constraints import discover_db_table
from tdda.constraints.db.drivers import (database_connection, parse_table_name,
                                         DATABASE_USAGE)


def discover_constraints_from_database(table, constraints_path=None,
                                       conn=None, dbtype=None, db=None,
                                       host=None, port=None, user=None,
                                       password=None, **kwargs):
    """
    Discover constraints in the given database table.

    Writes constraints as JSON to the specified file (or to stdout).
    """
    (table, dbtype) = parse_table_name(table, dbtype)
    db = database_connection(table=table, conn=conn, dbtype=dbtype, db=db,
                             host=host, port=port,
                             user=user, password=password)
    constraints = discover_db_table(dbtype, db, table, **kwargs)
    if constraints_path:
        with open(constraints_path, 'w') as f:
            f.write(constraints.to_json())
    else:
        print(constraints.to_json())


def get_params(args):
    params = {
        'table': None,
        'constraints_path': None,
        'inc_rex': False,
        'conn': None,
        'dbtype': None,
        'db': None,
        'host': None,
        'port': None,
        'user': None,
        'password': None,
    }
    parser = argparse.ArgumentParser(prog='tdda discover')
    parser.add_argument('-?', '--?', action='help',
                        help='same as -h or --help')
    parser.add_argument('-r', '--rex', action='store_true',
                        help='include regular expression generation')
    parser.add_argument('-R', '--norex', action='store_true',
                        help='exclude regular expression generation')
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
    parser.add_argument('constraints', nargs='?',
                        help='name of constraints file to create')
    flags, more = parser.parse_known_args(args)

    if flags.rex:
        params['inc_rex'] = True
    elif flags.norex:
        params['inc_rex'] = False
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


class DatabaseDiscoverer:
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def discover(self):
        params = get_params(self.argv[1:])
        discover_constraints_from_database(**params)


def main(argv):
    if len(argv) > 1 and argv[1] in ('-v', '--version'):
        print(__version__)
        sys.exit(0)
    d = DatabaseDiscoverer(argv)
    d.discover()


if __name__ == '__main__':
    main(sys.argv)
