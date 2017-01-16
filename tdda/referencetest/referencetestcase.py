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
            self.set_data_location('/data')

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
        unittest.main(argv=set_write_from_argv())


def set_write_from_argv(argv=None):
    """
    This is used to set the class's write flag if a -w or -W option
    is passed on the command line, either using the argv provided,
    or sys.argv otherwise.

    The -W option takes no parameters, and turns on reference-regeneration
    for all kinds of results.

    The -w option takes a list of parameter, constisting of names of
    of result kinds to be regenerated. The names can be separate parameters,
    or they can be a single comma-separated parameter.

    The framework reports on each file being regenerated, by default. Use
    The -wquiet option to make it rewrite files quietly.

    Also recognizes --w, --W and --wquiet, for compatibility with the pytest
    interface.

    argv or sys.argv is returned, with any '-w' or '-W' removed.
    """
    if argv is None:
        argv = sys.argv
    if '-wquiet' in argv or '--wquiet' in argv:
        idx = argv.index('-wquiet') or argv.index('--wquiet')
        ReferenceTestCase.set_defaults(verbose=False)
        argv = argv[:idx] + argv[idx+1:]
    if '-W' in argv or '--W' in argv:
        idx = argv.index('-W') or argv.index('--W')
        ReferenceTestCase.set_regeneration()
        return argv[:idx] + argv[idx+1:]
    elif '-w' in argv or '--w' in argv:
        idx = argv.index('-w') or argv.index('--w')
        if idx < len(argv) - 1:
            for r in argv[idx+1:]:
                for kind in r.split(','):
                    ReferenceTestCase.set_regeneration(kind)
        else:
            raise Exception('-w option requires parameters; '
                            'use -W to regenerate all reference results')
        return argv[:idx]
    else:
        return argv


def main():
    """
    Wrapper around the unittest.main() entry point.
    """
    ReferenceTestCase.main()

