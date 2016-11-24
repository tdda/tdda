# -*- coding: utf-8 -*-

"""
referencetestcase.py: unittest interface to tdda reference testing.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016


This module provides the ReferenceTestCase class, which extends the
standard unittest.TestCase test-case class, adding methods for checking
correctness of files against reference data.

It also provides a main() function, which can be used to run (and
regenerate) reference tests which have been implemented using subclasses
of ReferenceTestCase.

When its main is run with -W or -w, it causes the framework to regenerate
reference data files. Different kinds of reference results can be regenerated
by passing in a comma-separated list of 'kind' names immediately afher the
-W or -w option. If no list of 'kind' names is provided, then all test results
will be regenerated.

For example:

    from tdda.referencetest.referencetestcase import ReferenceTestCase
    import my_module

    class MyTest(ReferenceTestCase):
        def __init__(self, *args, **kwargs):
            ReferenceTestCase.__init__(self, *args, **kwargs)
            self.set_data_location(None, '/data')

        def test_my_table_function(self):
            result = my_module.my_function()
            self.assertStringCorrect(result, 'result.txt', kind='table')

        def test_my_graph_function(self):
            result = my_module.my_function()
            self.assertStringCorrect(result, 'result.txt', kind='graph')

    if __name__ == '__main__':
        ReferenceTestCase.main()

Run it to regenerate the reference results (or generate them for the
first time) with:

    # regenerate all the reference test results
    python my_test.py -w

    # regenerate just the 'table' reference test results
    python my_test.py -wtable

    # regenerate both 'table' and 'graph' reference tests, explicitly.
    python my_test.py -wtable,graph
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys
import unittest

from tdda.referencetest.referencetest import ReferenceTest


class ReferenceTestCase(unittest.TestCase, ReferenceTest):
    """
    Wrapper around the ReferenceTest class to allow it to operate as
    a test-case class using the unittest testing framework.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializer for a ReferenceTestCase instance.
        """
        unittest.TestCase.__init__(self, *args, **kwargs)
        ReferenceTest.__init__(self, self.assertTrue)

    @staticmethod
    def main():
        """
        Wrapper around the unittest.main() entry point.
        """
        if len(sys.argv) > 1 and sys.argv[1][:2] in ('-W', '-w'):
            kinds = sys.argv[1][2:] or None
            if kinds:
                for k in kinds.split(','):
                    ReferenceTestCase.set_regeneration(k)
            else:
                ReferenceTestCase.set_regeneration()
            unittest.main(argv=[sys.argv[0]] + sys.argv[2:])
        else:
            unittest.main()

