# -*- coding: utf-8 -*-

"""
Test Suite for database constraints.

The tests will always run on SQLite, provided the sqlite3 python
module is available, which it will be on Mac, but won't necessarily
be on Linux or Windows).

The tests will run on Postgres and MySQL, provided that:
  - the appropriate python modiles (pgdb and MySQLDB) are available
  - the test data (from testdata/example) has been imported into the database
  - a database connection file (.tdda_db_conn_postgres, .tdda_db_conn_mysql)
    has been set up in your home directory, specifying the database name,
    the schema name for where the test data has been imported, and the
    user/password credentials.

The tests don't (yet) run on MongoDB.
"""

import json
import os
import sys
import unittest

try:
    import pgdb
except ImportError:
    print('Skipping Postgres tests (no driver library)', file=sys.stderr)
    pgdb = None

try:
    import MySQLdb
except ImportError:
    print('Skipping MySQL tests (no driver library)', file=sys.stderr)
    MySQLdb = None

try:
    import sqlite3
except ImportError:
    print('Skipping SQLite tests (no driver library)', file=sys.stderr)
    sqlite3 = None

try:
    import pymongo
except ImportError:
    #print('Skipping MongoDB tests (no driver library)', file=sys.stderr)
    pymongo = None
pymongo = None  # The tests don't yet work for MongoDB


from tdda.referencetest.referencetestcase import ReferenceTestCase, tag

from tdda.constraints.db.drivers import database_connection, DatabaseHandler
from tdda.constraints.db.constraints import (verify_db_table,
                                             discover_db_table)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA_DIR = os.path.join(os.path.dirname(THIS_DIR), 'testdata')


POSTGRES_CONN_FILE = os.path.join(os.path.expanduser('~'),
                                  '.tdda_db_conn_postgres')
MYSQL_CONN_FILE = os.path.join(os.path.expanduser('~'),
                              '.tdda_db_conn_mysql')
MONGODB_CONN_FILE = os.path.join(os.path.expanduser('~'),
                                 '.tdda_db_conn_mongodb')

isPython2 = sys.version_info[0] < 3

class TestDatabaseHandlers:
    """
    Mix-in class, to be used in a subclass that also inherits ReferenceTestCase
    """
    def test_connection(self):
        elements = self.dbh.resolve_table('elements')
        self.assertTrue(self.dbh.check_table_exists(elements))
        self.assertFalse(self.dbh.check_table_exists('does_not_exist'))

    def test_handler_simple_ops(self):
        elements = self.dbh.resolve_table('elements')
        names = self.dbh.get_database_column_names(elements)
        if '_rowindex' in names:
            names.remove('_rowindex')  # hidden field, ignore it
        self.assertEqual(names,
                         ['Z', 'Name', 'Symbol', 'Period', 'Group',
                          'ChemicalSeries', 'AtomicWeight', 'Etymology',
                          'RelativeAtomicMass', 'MeltingPointC',
                          'MeltingPointKelvin', 'BoilingPointC',
                          'BoilingPointF', 'Density', 'Description', 'Colour'])
        self.assertEqual(self.dbh.get_database_column_type(elements, 'Z'),
                         'int')
        self.assertEqual(self.dbh.get_database_column_type(elements, 'Name'),
                         'string')
        self.assertEqual(self.dbh.get_database_column_type(elements,
                                                           'Density'),
                         'real')
        self.assertEqual(self.dbh.get_database_nrows(elements), 118)
        self.assertEqual(self.dbh.get_database_nnull(elements, 'Colour'), 85)
        self.assertEqual(self.dbh.get_database_nnonnull(elements, 'Colour'),
                         33)

    def test_handler_unique_values(self):
        elements = self.dbh.resolve_table('elements')
        self.assertEqual(self.dbh.get_database_unique_values(elements,
                                                             'ChemicalSeries'),
                         ['Actinoid', 'Alkali metal', 'Alkaline earth metal',
                          'Halogen', 'Lanthanoid', 'Metalloid', 'Noble gas',
                          'Nonmetal', 'Poor metal', 'Transition metal'])


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDBHandlers(ReferenceTestCase, TestDatabaseHandlers):
    @classmethod
    def setUpClass(cls):
        dbfile = os.path.join(TESTDATA_DIR, 'example.db')
        db = database_connection(dbtype='sqlite', db=dbfile)
        cls.dbh = DatabaseHandler('sqlite', db)


@unittest.skipIf(pgdb is None or not os.path.exists(POSTGRES_CONN_FILE),
                 'pgdb not available, or no tdda postgres connection file')
class TestPostgresDBHandlers(ReferenceTestCase, TestDatabaseHandlers):
    @classmethod
    def setUpClass(cls):
        db = database_connection(dbtype='postgres')
        cls.dbh = DatabaseHandler('postgres', db)


@unittest.skipIf(MySQLdb is None or not os.path.exists(MYSQL_CONN_FILE),
                 'MySDLdb not available, or no tdda mysql connection file')
class TestMySQLDBHandlers(ReferenceTestCase, TestDatabaseHandlers):
    @classmethod
    def setUpClass(cls):
        db = database_connection(dbtype='mysql')
        cls.dbh = DatabaseHandler('mysql', db)


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDatabaseConnectionFile(unittest.TestCase):
    def test_sqlite_connection_from_file(self):
        connfile = os.path.join(TESTDATA_DIR, 'sqlite.conn')
        db = database_connection(conn=connfile)
        dbh = DatabaseHandler('sqlite', db)
        elements = dbh.resolve_table('elements')
        self.assertTrue(dbh.check_table_exists(elements))
        self.assertFalse(dbh.check_table_exists('does_not_exist'))


@unittest.skipIf(pymongo is None or not os.path.exists(MONGODB_CONN_FILE),
                 'MongoDB not available, or no tdda mongodb connection file')
class TestMongoDBHandlers(ReferenceTestCase, TestDatabaseHandlers):
    @classmethod
    def setUpClass(cls):
        db = database_connection(dbtype='mongodb')
        cls.dbh = DatabaseHandler('mongodb', db)


class TestDatabaseConstraintVerifiers:
    """
    Mix-in class, to be used in a subclass that also inherits ReferenceTestCase
    """
    def test_verify_elements(self):
        # check the full 118 using constraints built on just 92
        constraints_file = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        elements = self.dbh.resolve_table('elements')
        result = verify_db_table(self.dbh.dbtype, self.db, elements,
                                 constraints_file, testing=True)
        self.assertEqual(result.passes, 57)
        self.assertEqual(result.failures, 15)

    def test_verify_elements_rex(self):
        # check the full 118 using constraints built on just 92, but
        # also including regex constraints - and using constraints that
        # were built using pandas, so there are some type differences too.
        constraints_file = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        elements = self.dbh.resolve_table('elements')
        result = verify_db_table(self.dbh.dbtype, self.db, elements,
                                 constraints_file, testing=True)

        self.assertEqual(result.passes, 58)    # the original 57, minus the
                                               # type (and min and max) ones
                                               # on the Group field, which
                                               # the constraints (wrongly)
                                               # claim to be a real field,
                                               # rather than integer... but
                                               # also including three new
                                               # passing regex constraints

        self.assertEqual(result.failures, 20)  # the original 15, plus
                                               # the three additional failures
                                               # because of type mismatch
                                               # on the Group field, and
                                               # two failing regexps because
                                               # of having more elements.

        for field in result.fields.values():
            for name, value in field.items():
                self.assertEqual(type(value), bool)


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDBConstraintVerifiers(ReferenceTestCase,
                                      TestDatabaseConstraintVerifiers):
    @classmethod
    def setUpClass(cls):
        dbfile = os.path.join(TESTDATA_DIR, 'example.db')
        cls.db = database_connection(dbtype='sqlite', db=dbfile)
        cls.dbh = DatabaseHandler('sqlite', cls.db)


class TestDatabaseConstraintDiscoverers:
    """
    Mix-in class, to be used in a subclass that also inherits ReferenceTestCase
    """
    def test_discover_elements(self):
        # build constraints for full 118 element dataset
        elements = self.dbh.resolve_table('elements')
        constraints = discover_db_table(self.dbh.dbtype, self.db, elements,
                                        inc_rex=False)
        constraints.remove_field('_rowindex') # hidden field, ignore it
        self.assertStringCorrect(constraints.to_json(),
                                 'elements118.tdda',
                                 rstrip=True,
                                 ignore_substrings=['"as_at":',
                                                    '"local_time":',
                                                    '"utc_time":',
                                                    '"creator":',
                                                    '"host":',
                                                    '"user":',
                                                    '"source":',
                                                    '"rdbms":',
                                                    '"dataset":',
                                                    '"tddafile":'])

    def test_discover_elements_rex(self):
        # build constraints for full 118 element dataset
        elements = self.dbh.resolve_table('elements')
        constraints = discover_db_table(self.dbh.dbtype, self.db, elements,
                                        inc_rex=True, seed=827364)
        constraints.remove_field('_rowindex') # hidden field, ignore it
        j = constraints.to_json()
        # compare against the right expected file, depending on whether the
        # version of python we're running under has escaped commas or not.
        if isPython2:
            expected_file = ('elements118oldrex.tdda' if '\\,' in j
                             else 'elements118rex.tdda')
        else:
            expected_file = ('elements118oldrex-3.tdda' if '\\,' in j
                             else 'elements118rex-3.tdda')
        self.assertStringCorrect(j, expected_file, rstrip=True,
                                 ignore_substrings=['"as_at":',
                                                    '"local_time":',
                                                    '"utc_time":',
                                                    '"creator":',
                                                    '"host":',
                                                    '"user":',
                                                    '"source":',
                                                    '"rdbms":',
                                                    '"dataset":',
                                                    '"tddafile":'])


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDBConstraintDiscoverers(ReferenceTestCase,
                                        TestDatabaseConstraintDiscoverers):
    @classmethod
    def setUpClass(cls):
        dbfile = os.path.join(TESTDATA_DIR, 'example.db')
        cls.db = database_connection(dbtype='sqlite', db=dbfile)
        cls.dbh = DatabaseHandler('sqlite', cls.db)


@unittest.skipIf(pgdb is None or not os.path.exists(POSTGRES_CONN_FILE),
                 'pgdb not available, or no tdda postgres connection file')
class TestPostgresDBConstraintDiscoverers(ReferenceTestCase,
                                          TestDatabaseConstraintDiscoverers):
    @classmethod
    def setUpClass(cls):
        cls.db = database_connection(dbtype='postgres')
        cls.dbh = DatabaseHandler('postgres', cls.db)


@unittest.skipIf(MySQLdb is None or not os.path.exists(MYSQL_CONN_FILE),
                 'MySDLdb not available, or no tdda mysql connection file')
class TestMySQLDBConstraintDiscoverers(ReferenceTestCase,
                                       TestDatabaseConstraintDiscoverers):
    @classmethod
    def setUpClass(cls):
        cls.db = database_connection(dbtype='mysql')
        cls.dbh = DatabaseHandler('mysql', cls.db)


@unittest.skipIf(pymongo is None or not os.path.exists(MONGODB_CONN_FILE),
                 'MongoDB not available, or no tdda mongodb connection file')
class TestMongoDBConstraintDiscoverers(ReferenceTestCase,
                                       TestDatabaseConstraintDiscoverers):
    @classmethod
    def setUpClass(cls):
        cls.db = database_connection(dbtype='mongodb')
        cls.dbh = DatabaseHandler('mongodb', cls.db)


TestSQLiteDBConstraintDiscoverers.set_default_data_location(TESTDATA_DIR)
TestPostgresDBConstraintDiscoverers.set_default_data_location(TESTDATA_DIR)
TestMySQLDBConstraintDiscoverers.set_default_data_location(TESTDATA_DIR)
TestMongoDBConstraintDiscoverers.set_default_data_location(TESTDATA_DIR)


if __name__ == '__main__':
    ReferenceTestCase.main()

