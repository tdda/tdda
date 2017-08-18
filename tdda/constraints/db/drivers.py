# -*- coding: utf-8 -*-

"""
Common database library support
"""

from __future__ import division
from __future__ import print_function

import datetime
import getpass
import json
import os
import re
import sys

try:
    import pgdb
except ImportError:
    pgdb = None

try:
    import MySQLdb
except ImportError:
    MySQLdb = None

try:
    import sqlite3
except ImportError:
    sqlite3 = None

try:
    import pymongo
except ImportError:
    pymongo = None

from tdda.constraints.base import UNICODE_TYPE
from tdda.constraints.flags import (discover_parser, discover_flags,
                                    verify_parser, verify_flags)


DATABASE_USAGE = '''

Database connection flags:

  * -conn FILE              Database connection file
  * -dbtype DBTYPE          Type of database
  * -db DATABASE            Name of database to connect to
  * -host HOSTNAME          Name of server to connect to
  * -port PORTNUMBER        IP port number to connect to
  * -user USERNAME          Username to connect as
  * -password PASSWORD      Password to authenticate with

If -conn is provided, then none of the other options are required, and
the database connection details are read from the specified file.

If the database type is specified (with the -dbtype option, or by
prefixing the table name, such as postgresql:mytable), then a default
connection file .tdda_db_conn_DBTYPE (in your home directory) is used,
if present.

'''


def parse_table_name(table, dbtype):
    """
    split a qualified table name into its two parts: the database type
    and the table name.
    """
    if ':' in table:
        parts = table.split(':')
        if dbtype is None:
            dbtype = parts[0].lower()
        table = parts[1]
    return (table, dbtype)


def applicable(argv):
    """
    Does a command line include parameters that are applicable for databases
    that are supported by these extensions?
    """
    for i, a in enumerate(argv):
        if ':' in a:
            (table, dbtype) = parse_table_name(a, None)
            if dbtype in DATABASE_HANDLERS:
                return True
        elif a == '-dbtype':
            return (i < len(argv) - 1
                    and argv[i+1] in DATABASE_HANDLERS)
    return '-db' in argv


def database_arg_parser(create_parser, usage):
    parser = create_parser(usage + DATABASE_USAGE)
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
    return parser


def database_arg_flags(create_flags, parser, args, params):
    params.update({
        'conn': None,
        'dbtype': None,
        'db': None,
        'host': None,
        'port': None,
        'user': None,
        'password': None,
    })
    flags = create_flags(parser, args, params)
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
    return flags


def database_connection(table=None, conn=None, dbtype=None, db=None,
                        host=None, port=None, user=None, password=None):
    """
    Connect to a database, using an appropriate driver for the type
    of database specified.
    """
    if conn:
        defaults = Connection(conn)
    else:
        if dbtype:
            dbtypelower = dbtype.lower()
            connfile = os.path.join(os.path.expanduser('~'),
                                    '.tdda_db_conn' + '_' + dbtypelower)
            if dbtypelower == 'postgres' and not os.path.exists(connfile):
                connfile = os.path.join(os.path.expanduser('~'),
                                        '.tdda_db_conn_postgresql')
        else:
            connfile = os.path.join(os.path.expanduser('~'), '.tdda_db_conn')
        if os.path.exists(connfile):
            defaults = Connection(connfile)
        else:
            defaults = None
    if defaults:
        if dbtype is None:
            dbtype = defaults.dbtype
        if db is None:
            db = defaults.db
        if host is None:
            host = defaults.host
        if port is None:
            port = defaults.port
        if user is None:
            user = defaults.user
        if password is None:
            password = defaults.password

    if host and (':' in host) and port is None:
        parts = host.split(':')
        host = parts[0]
        port = int(parts[1])
    if port is not None:
        port = int(port)

    if dbtype is None:
        print('Database type required ("-dbtype type")', file=sys.stderr)
        sys.exit(1)
    if db is None:
        print('Database name required ("-db name")', file=sys.stderr)
        sys.exit(1)

    dbtypelower = dbtype.lower()
    if dbtypelower in DATABASE_CONNECTORS:
        connector = DATABASE_CONNECTORS[dbtypelower]
        return connector(host, port, db, user, password)
    else:
        print('Database type %s not supported' % dbtype, file=sys.stderr)
        sys.exit(1)


def database_connection_postgres(host, port, db, user, password):
    if pgdb:
        if port is not None:
            host = host + ':' + str(port)
        return pgdb.connect(host=host, database=db,
                            user=user, password=password)
    else:
        print('PostgreSQL driver not available', file=sys.stderr)
        sys.exit(1)


def database_connection_mysql(host, port, db, user, password):
    if MySQLdb:
        # TODO: should provide support for MySQL 'option-files' too.
        if host is None:
            host = 'localhost'
        if port is None:
            port = 3306
        if user is None:
            user = getpass.getuser()
        if password:
            try:
                return MySQLdb.connect(host=host, port=port, db=db,
                                       user=user, password=password)
            except:
                # some versions of the MySQL driver use different names
                return MySQLdb.connect(host=host, port=port, db=db,
                                       username=user, passwd=password)
        else:
            return MySQLdb.connect(host=host, port=port, db=db, user=user)
    else:
        print('MySQL driver not available', file=sys.stderr)


def database_connection_sqlite(host, port, db, user, password):
    if sqlite3:
        conn = sqlite3.connect(db)
        conn.create_function('regexp', 2, regex_matcher)
        return conn
    else:
        print('sqlite driver not available', file=sys.stderr)
        sys.exit(1)


def database_connection_mongodb(host, port, db, user, password):
    if pymongo:
        if host is None:
            host = 'localhost'
        if port is None:
            port = 27017
        client = pymongo.MongoClient(host, port)
        if db not in client.database_names():
            print('Mongodb database %s does not exist' % db)
            sys.exit(1)
        return client[db]
    else:
        print('mongodb driver not available', file=sys.stderr)
        sys.exit(1)


def regex_matcher(expr, item):
    """
    REGEXP implementation for Sqlite
    """
    if item is None:
        return False
    else:
        return re.match(expr, item) is not None


class Connection:
    """
    Class for reading a connection specification file.
    """
    def __init__(self, filename):
        with open(filename) as f:
            d = json.loads(f.read())
        self.dbtype = d.get('dbtype')
        self.db = d.get('db')
        self.host = d.get('host')
        self.port = d.get('port')
        self.user = d.get('user')
        self.password = d.get('password')

        if (self.dbtype and self.dbtype.lower() == 'sqlite'
                    and self.db is not None
                    and not os.path.isabs(self.db)):
            # if a .conn file for a sqlite connection specifies a .db file,
            # then resolve that relative to the location of the .conn file.
            self.db = os.path.join(os.path.dirname(filename), self.db)


class DatabaseHandler:
    """
    Common SQL and NoSQL database support
    """
    def __init__(self, dbtype, db):
        handlerClass = self.check_db_type(dbtype)
        self.instance = handlerClass(dbtype, db)

    def check_db_type(self, dbtype):
        """
        Check that this is one of the database types that we recognize
        """
        if dbtype in DATABASE_HANDLERS:
            return DATABASE_HANDLERS[dbtype]
        else:
            raise Exception('Unsupported database type')

    def __getattr__(self, name):
        return getattr(self.instance, name)


# TODO: this is too specific to Miro stuff
RESERVED_WORDS = ('group')


class SQLDatabaseHandler:
    """
    Common database SQL support
    """
    def __init__(self, dbtype, db):
        self.dbtype = dbtype
        self.db = db
        self.cursor = db.cursor()

    def canon(self, name):
        # 'canonicalise' a database table name
        name = name.lower()
        if name in RESERVED_WORDS:
            name = name + '_'
        return name

    def execute_scalar(self, sql):
        # execute a SQL statement, returning a single scalar result
        self.cursor.execute(sql)
        result = self.cursor.fetchall()[0][0]
        if result == '' and self.dbtype == 'sqlite':
            result = None
        return result

    def execute_all(self, sql):
        # execute a SQL statement, returning a list of rows
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def db_value_is_null(self, value):
        return value is None

    def db_value_to_datetime(self, value):
        return value

    def check_table_exists(self, tablename):
        """
        Check that a table (or a schema.table) exists.
        """
        if '.' in tablename:
            parts = tablename.split('.')
            if len(parts) == 1:
                schema = None
                table = tablename
            elif len(parts) == 2:
                schema = parts[0]
                table = parts[1]
            else:
                raise Exception('Bad table format %s' % tablename)
        else:
            schema = None
            table = tablename
        if self.dbtype in ('postgres', 'postgresql'):
            if schema is None:
                schema = 'public'
            sql = '''SELECT COUNT(*) FROM pg_catalog.pg_class c
                     LEFT JOIN pg_catalog.pg_namespace n
                     ON n.oid = c.relnamespace
                     WHERE c.relkind IN ('r', '', 'v')
                     AND c.relname = '%s'
                     AND n.nspname = '%s';''' % (table, schema)
        elif self.dbtype == 'mysql':
            if schema:
                sql = '''SELECT COUNT(*) FROM information_schema.tables
                         WHERE table_schema = '%s'
                         AND table_name = '%s';''' % (schema, table)
            else:
                sql = '''SELECT COUNT(*) FROM information_schema.tables
                         WHERE table_name = '%s';''' % table
        elif self.dbtype == 'sqlite':
            sql = '''SELECT COUNT(*) FROM sqlite_master
                            WHERE (type = 'table' OR type='view')
                            AND name = '%s';''' % tablename
        else:
            raise Exception('Unsupported database type %s' % self.dbtype)
        return self.execute_scalar(sql) > 0

    def get_database_column_names(self, tablename):
        if self.dbtype in ('postgres', 'postgresql'):
            sql = '''
                SELECT a.attname FROM pg_attribute a
                WHERE a.attrelid = '%s'::regclass AND a.attnum > 0
                ORDER BY a.attnum;
                ''' % tablename
            rows = self.execute_all(sql)
            return [r[0] for r in rows]
        elif self.dbtype == 'mysql':
            sql = '''
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE table_name = '%s';
                ''' % tablename
            rows = self.execute_all(sql)
            return [r[0] for r in rows]
        elif self.dbtype == 'sqlite':
            sql = 'PRAGMA table_info(%s)' % tablename
            rows = self.execute_all(sql)
            return [r[1] for r in rows]
        else:
            raise Exception('Unsupported database type')

    def get_database_column_type(self, tablename, colname):
        typeMap = {
            'int'        : 'int',
            'int4'       : 'int',
            'int8'       : 'int',
            'smallint'   : 'int',
            'bigint'     : 'int',
            'integer'    : 'int',
            'float'      : 'real',
            'float4'     : 'real',
            'float8'     : 'real',
            'float16'    : 'real',
            'double'     : 'real',
            'numeric'    : 'real',
            'real'       : 'real',
            'bool'       : 'bool',
            'text'       : 'string',
            'varchar'    : 'string',
            'char'       : 'string',
            'name'       : 'string',
            'oidvector'  : 'string',
            'timestamp'  : 'date',
            'date'       : 'date',
            None         : None,
        }
        if self.dbtype in ('postgres', 'postgresql'):
            sql = '''
                SELECT t.typname
                FROM pg_attribute a inner join pg_type t on a.atttypid = t.oid
                WHERE a.attrelid = '%s'::regclass AND a.attnum > 0
                                                  AND a.attname = '%s'
                ORDER BY a.attnum;
                ''' % (tablename, self.canon(colname))
            typeresult = self.execute_scalar(sql)
        elif self.dbtype == 'mysql':
            sql = '''
                SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
                WHERE table_name = '%s' AND COLUMN_NAME = '%s';
                ''' % (tablename, self.canon(colname))
            typeresult = self.execute_scalar(sql)
        elif self.dbtype == 'sqlite':
            result = self.execute_all('PRAGMA table_info(%s)' % tablename)
            typeresult = None
            for row in result:
                if self.canon(row[1]) == self.canon(colname):
                    typeresult = row[2]
                    break
        else:
            raise Exception('Unsupported database type')
        return typeMap[typeresult.lower()]

    def get_database_nrows(self, tablename):
        sql = 'SELECT COUNT(*) FROM %s' % tablename
        return self.execute_scalar(sql)

    def get_database_nnull(self, tablename, colname):
        sql = ('SELECT COUNT(*) FROM %s WHERE %s IS NULL'
               % (tablename, self.canon(colname)))
        return self.execute_scalar(sql)

    def get_database_nnonnull(self, tablename, colname):
        sql = ('SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL'
               % (tablename, self.canon(colname)))
        return self.execute_scalar(sql)

    def get_database_min(self, tablename, colname):
        sql = 'SELECT MIN(%s) FROM %s' % (self.canon(colname), tablename)
        return self.execute_scalar(sql)

    def get_database_max(self, tablename, colname):
        sql = 'SELECT MAX(%s) FROM %s' % (self.canon(colname), tablename)
        return self.execute_scalar(sql)

    def get_database_min_length(self, tablename, colname):
        sql = 'SELECT MIN(LENGTH(%s)) FROM %s' % (self.canon(colname),
                                                  tablename)
        return self.execute_scalar(sql)

    def get_database_max_length(self, tablename, colname):
        sql = 'SELECT MAX(LENGTH(%s)) FROM %s' % (self.canon(colname),
                                                  tablename)
        return self.execute_scalar(sql)

    def get_database_nunique(self, tablename, colname):
        colname = self.canon(colname)
        sql = ('SELECT COUNT(DISTINCT %s) FROM %s WHERE %s IS NOT NULL'
               % (colname, tablename, self.canon(colname)))
        return self.execute_scalar(sql)

    def get_database_unique_values(self, tablename, colname,
                                   sorted_values=True, include_nulls=False):
        colname = self.canon(colname)
        whereclause = ('' if include_nulls
                       else 'WHERE %s IS NOT NULL' % colname)
        orderby = ('ORDER BY %s ASC' % colname) if sorted_values else ''
        sql = 'SELECT DISTINCT %s FROM %s %s %s' % (colname, tablename,
                                                    whereclause, orderby)
        result = self.execute_all(sql)
        return [x[0] for x in result]

    def get_database_rex_match(self, tablename, colname, rexes):
        if rexes is None:      # a null value is not considered to be an
            return True        # active constraint, so is always satisfied
        name = self.canon(colname)
        if self.dbtype in ('postgres', 'postgresql'):
            # postgresql uses ~ syntax
            rexprs = ["(%s ~ '%s')" % (name, r) for r in rexes]
        elif self.dbtype == 'mysql':
            # mysql uses REGEXP syntax, and doesn't understand \d
            rexes = [r.replace('\\d', '[0-9]') for r in rexes]
            rexprs = ["(%s REGEXP '%s')" % (name, r) for r in rexes]
        elif self.dbtype == 'sqlite':
            # sqlite doesn't support regular expressions unless the
            # regexp() user-defined function is available - but we have
            # arranged for that in the database_connection_mongodb function.
            rexprs = ["(%s REGEXP '%s')" % (name, r) for r in rexes]
        else:
            raise Exception('Unsupported database type')

        sql = ('SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL AND NOT(%s)'
               % (tablename, name, ' OR '.join(rexprs)))
        return self.execute_scalar(sql) == 0


class MongoDBDatabaseHandler:
    """
    NoSQL MonggoDB support
    """
    def __init__(self, dbtype, db):
        self.dbtype = dbtype
        self.db = db

    def find_collection(self, tablename):
        """
        Search through the collections hierarchy to resolve dotted names
        """
        parts = tablename.split('.')
        collection = self.db
        for p in parts:
            collection = collection[p]
        return collection

    def check_table_exists(self, tablename):
        try:
            self.find_collection(tablename)
            return True
        except pymongo.errors.InvalidName:
            return False

    def get_database_column_names(self, tablename):
        collection = self.find_collection(tablename)
        mapfn = '''function() {
                        var keys = [];
                        for (var k in this) {
                            keys.push(k);
                        }
                        emit(null, keys);
                   }'''
        redfn = '''function(key, values) {
                       var keyset = {};
                       for (var i = 0; i < values.length; i++) {
                           for (var j = 0; j < values[i].length; j++) {
                               keyset[values[i][j]] = true;
                           }
                       }
                       var keys = [];
                       for (var k in keyset) {
                           if (k != '_id') {
                               keys.push(k);
                           }
                       }
                       return JSON.stringify(keys);
                   }'''
        v = collection.map_reduce(mapfn, redfn, 'inline').find_one()['value']
        # this mongodb map/reduce op returns a json repr of the list of keys
        return json.loads(v)

    def get_database_column_type(self, tablename, colname):
        collection = self.find_collection(tablename)
        doc = collection.find_one({colname: {'$ne': None}})
        if doc:
            val = doc[colname]
            valtype = type(val)
            if valtype == bool:
                return 'bool'
            elif valtype in (int, long):
                return 'int'
            elif valtype == float:
                return 'real'
            elif valtype in (str, UNICODE_TYPE):
                return 'string'
            elif isinstance(val, datetime.datetime):
                return 'date'
            else:
                return 'other'
        else:
            return None

    def get_database_nrows(self, tablename):
        collection = self.find_collection(tablename)
        return collection.count()

    def get_database_nnull(self, tablename, colname):
        collection = self.find_collection(tablename)
        return collection.find({colname: {'$eq': None}}).count()

    def get_database_nnonnull(self, tablename, colname):
        collection = self.find_collection(tablename)
        return collection.find({colname: {'$ne': None}}).count()

    def get_database_nunique(self, tablename, colname):
        collection = self.find_collection(tablename)
        #return len(collection.distinct(colname))
        return collection.aggregate([
            {'$match': {colname: {'$exists': True}}},
            {'$match': {colname: {'$ne': None}}},
            {'$group': {'_id': '$' + colname}},
            {'$group': {'_id': None, 'nunique': {'$sum': 1}}},
        ]).next()['nunique']

    def get_database_unique_values(self, tablename, colname,
                                   sorted_values=True):
        collection = self.find_collection(tablename)
        values = collection.distinct(colname)
        return sorted(values) if sorted_values else values

    def get_database_min_length(self, tablename, colname):
        collection = self.find_collection(tablename)
        mapfn = 'function() { emit(null, this.name ? this.name.length : null);}'
        redfn = 'function(key, values) { return Math.min.apply(Math, values);}'
        v = collection.map_reduce(mapfn, redfn, 'inline').find_one()['value']
        return int(v)

    def get_database_max_length(self, tablename, colname):
        collection = self.find_collection(tablename)
        mapfn = 'function() { emit(null, this.name ? this.name.length: null);}'
        redfn = 'function(key, values) { return Math.max.apply(Math, values);}'
        v = collection.map_reduce(mapfn, redfn, 'inline').find_one()['value']
        return int(v)

    def get_database_min(self, tablename, colname):
        collection = self.find_collection(tablename)
        return collection.aggregate([
            {'$match': {colname: {'$exists': True}}},
            {'$group': {'_id': None, 'min': {'$min': '$' + colname}}},
        ]).next()['min']

    def get_database_max(self, tablename, colname):
        collection = self.find_collection(tablename)
        return collection.aggregate([
            {'$match': {colname: {'$exists': True}}},
            {'$group': {'_id': None, 'max': {'$max': '$' + colname}}},
        ]).next()['max']

    def db_value_is_null(self, value):
        return value is None

    def db_value_to_datetime(self, value):
        return value


DATABASE_CONNECTORS = {
    'postgres': database_connection_postgres,
    'postgresql': database_connection_postgres,
    'mysql': database_connection_mysql,
    'sqlite': database_connection_sqlite,
    'mongodb': database_connection_mongodb
}

DATABASE_HANDLERS = {
    'postgres': SQLDatabaseHandler,
    'postgresql': SQLDatabaseHandler,
    'mysql': SQLDatabaseHandler,
    'sqlite': SQLDatabaseHandler,
    'mongodb': MongoDBDatabaseHandler,
}

