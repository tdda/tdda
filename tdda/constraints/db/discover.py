# -*- coding: utf-8 -*-

"""
Support for database constraint discovery from the command-line tool

Discover TDDA constraints for database tables, and save the generated
constraints as a .tdda JSON file.

"""

USAGE = '''

Parameters:

  * table is one of:

     - a database table name
     - a schema-qualified table name of the form schema.table
     - a database table name qualified by database type, of the
       form dbtype:table or dbtype:schema.table

  * constraints.tdda, if provided, specifies the name of a file to
    which the generated constraints will be written.

'''

import os
import sys

from tdda import __version__
from tdda.constraints.flags import discover_parser, discover_flags
from tdda.constraints.db.constraints import discover_db_table
from tdda.constraints.db.drivers import (database_connection, parse_table_name,
                                         database_arg_parser,
                                         database_arg_flags)


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
    if constraints is None:
        # should never happen
        return

    output = constraints.to_json(tddafile=constraints_path)

    if constraints_path:
        with open(constraints_path, 'w') as f:
            f.write(output);
    else:
        print(output)
    return output


def get_params(args):
    parser = database_arg_parser(discover_parser, USAGE)
    parser.add_argument('table', nargs=1, help='database table name')
    parser.add_argument('constraints', nargs='?',
                        help='name of constraints file to create')
    params = {}
    flags = database_arg_flags(discover_flags, parser, args, params)
    params['table'] = flags.table[0] if flags.table else None
    params['constraints_path'] = flags.constraints
    return params


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
