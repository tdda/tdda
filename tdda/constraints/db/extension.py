# -*- coding: utf-8 -*-

"""
Extensions to the ``tdda`` command line tool, to support databases.
"""

import sys

from tdda.constraints.extension import ExtensionBase

from tdda.constraints.db.drivers import applicable
from tdda.constraints.db.discover import DatabaseDiscoverer
from tdda.constraints.db.verify import DatabaseVerifier
from tdda.constraints.db.detect import DatabaseDetector


class TDDADatabaseExtension(ExtensionBase):
    def __init__(self, argv, verbose=False):
        ExtensionBase.__init__(self, argv, verbose=verbose)

    def applicable(self):
        return applicable(self.argv)

    def help(self, stream=sys.stdout):
        print('  - Tables from PostgreSQL databases (postgres:tablename)',
              file=stream)
        print('  - Tables from MySQL databases (mysql:tablename)',
              file=stream)
        print('  - Tables from SQLite databases (sqlite:tablename)',
              file=stream)
        print('  - Collections from MongoDB NoSQL databases '
              '(mongodb:collection)', file=stream)

    def spec(self):
        return 'DBTYPE:tablename, or -dbtype DBTYPE and a database table'

    def discover(self):
        return DatabaseDiscoverer(self.argv, verbose=self.verbose).discover()

    def verify(self):
        return DatabaseVerifier(self.argv, verbose=self.verbose).verify()

    def detect(self):
        return DatabaseDetector(self.argv, verbose=self.verbose).detect()

