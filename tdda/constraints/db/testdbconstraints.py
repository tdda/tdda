# -*- coding: utf-8 -*-

"""
Test Suite for database constraints.

The tests only use SqlLite, since that can be used in a contained way, without
depending on having set up any database server.
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import json
import os
import unittest

try:
    import sqlite3
except ImportError:
    sqlite3 = None


from tdda.referencetest.referencetestcase import ReferenceTestCase

from tdda.constraints.db.drivers import database_connection, DatabaseHandler
from tdda.constraints.db.constraints import (verify_db_table,
                                             discover_db_table)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA_DIR = os.path.join(os.path.dirname(THIS_DIR), 'testdata')


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDatabaseHandlers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbfile = os.path.join(TESTDATA_DIR, 'example.db')
        db = database_connection(dbtype='sqlite', db=dbfile)
        cls.dbh = DatabaseHandler('sqlite', db)

    def test_sqlite_connection(self):
        self.assertTrue(self.dbh.check_table_exists('elements'))
        self.assertFalse(self.dbh.check_table_exists('does_not_exist'))

    def test_sqlite_handler_simple_ops(self):
        self.assertEqual(self.dbh.get_database_column_names('elements'),
                         ['z', 'name', 'symbol', 'period', 'group_',
                          'chemicalseries', 'atomicweight', 'etymology',
                          'relativeatomicmass', 'meltingpointc',
                          'meltingpointkelvin', 'boilingpointc',
                          'boilingpointf', 'density', 'description', 'colour'])
        self.assertEqual(self.dbh.get_database_column_type('elements', 'z'),
                         'int')
        self.assertEqual(self.dbh.get_database_column_type('elements', 'name'),
                         'string')
        self.assertEqual(self.dbh.get_database_column_type('elements',
                                                           'density'),
                         'real')
        self.assertEqual(self.dbh.get_database_nrows('elements'), 118)
        self.assertEqual(self.dbh.get_database_nnull('elements', 'colour'), 85)
        self.assertEqual(self.dbh.get_database_nnonnull('elements', 'colour'),
                         33)

    def test_sqlite_handler_unique_values(self):
        self.assertEqual(self.dbh.get_database_unique_values('elements',
                                                             'chemicalseries'),
                         ['Actinoid', 'Alkali metal', 'Alkaline earth metal',
                          'Halogen', 'Lanthanoid', 'Metalloid', 'Noble gas',
                          'Nonmetal', 'Poor metal', 'Transition metal'])


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDatabaseConnectionFile(unittest.TestCase):
    def test_sqlite_connection_from_file(self):
        connfile = os.path.join(TESTDATA_DIR, 'sqlite.conn')
        db = database_connection(conn=connfile)
        dbh = DatabaseHandler('sqlite', db)
        self.assertTrue(dbh.check_table_exists('elements'))
        self.assertFalse(dbh.check_table_exists('does_not_exist'))


@unittest.skipIf(sqlite3 is None, 'sqlite3 not available')
class TestSQLiteDatabaseConstraintVerifiers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbfile = os.path.join(TESTDATA_DIR, 'example.db')
        cls.db = database_connection(dbtype='sqlite', db=dbfile)

    def test_sqlite_verify_elements(self):
        # check the full 118 using constraints built on just 92
        constraints_file = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        result = verify_db_table('sqlite', self.db, 'elements',
                                 constraints_file, testing=True)
        self.assertEqual(result.passes, 57)
        self.assertEqual(result.failures, 15)

    def test_sqlite_verify_elements_rex(self):
        # check the full 118 using constraints built on just 92, but
        # also including regex constraints - and using constraints that
        # were built using pandas, so there are some type differences too.
        constraints_file = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        result = verify_db_table('sqlite', self.db, 'elements',
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
class TestSQLiteDatabaseConstraintDiscoverers(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        dbfile = os.path.join(TESTDATA_DIR, 'example.db')
        cls.db = database_connection(dbtype='sqlite', db=dbfile)

    def test_sqlite_discover_elements(self):
        # build constraints for full 118 element dataset
        constraints = discover_db_table('sqlite', self.db, 'elements',
                                        inc_rex=False)
        self.assertStringCorrect(constraints.to_json(), 'elements118.tdda',
                                 rstrip=True)

    def test_sqlite_discover_elements_rex(self):
        # build constraints for full 118 element dataset
        constraints = discover_db_table('sqlite', self.db, 'elements',
                                        inc_rex=True)
        self.assertStringCorrect(constraints.to_json(), 'elements118rex.tdda',
                                 rstrip=True)


TestSQLiteDatabaseConstraintDiscoverers.set_default_data_location(TESTDATA_DIR)


if __name__ == '__main__':
    ReferenceTestCase.main()

