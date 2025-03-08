# -*- coding: utf-8 -*-

"""This module provides the
:py:class:`~tdda.referencetest.referencetestcase.ReferenceTestCase` class,
which extends the
standard :py:class:`unittest.TestCase` test-case class, augmenting it
with methods for checking correctness of files against reference data.

It also provides a ``main()`` function, which can be used to run (and
regenerate) reference tests which have been implemented using subclasses
of ``ReferenceTestCase``.

For example::

    from tdda.referencetest import ReferenceTestCase
    import my_module

    class TestMyClass(ReferenceTestCase):
        def test_my_csv_function(self):
            result = my_module.my_csv_function(self.tmp_dir)
            self.assertCSVFileCorrect(result, 'result.csv')

        def test_my_pandas_dataframe_function(self):
            result = my_module.my_dataframe_function()
            self.assertDataFrameCorrect(result, 'result.csv')

        def test_my_table_function(self):
            result = my_module.my_table_function()
            self.assertStringCorrect(result, 'table.txt', kind='table')

        def test_my_graph_function(self):
            result = my_module.my_graph_function()
            self.assertStringCorrect(result, 'graph.txt', kind='graph')

    TestMyClass.set_default_data_location('testdata')

    if __name__ == '__main__':
        ReferenceTestCase.main()

Tagged Tests
~~~~~~~~~~~~

If the tests are run with the ``--tagged`` or ``-1`` (the digit one)
command-line option, then only tests that have been decorated with
``referencetest.tag``, are run. This is a mechanism for allowing
only a chosen subset of tests to be run, which is useful during
development. The ``@tag`` decorator can be applied to either test
classes or test methods.

If the tests are run with the ``--istagged`` or ``-0`` (the digit
zero) command-line option, then no tests are run; instead, the
framework reports the full module names of any test classes that have
been decorated with ``@tag``, or which contain any tests that have been
decorated with ``@tag``.

For example::

    from tdda.referencetest import ReferenceTestCase, tag
    import my_module

    class TestMyClass1(ReferenceTestCase):
        @tag
        def test_a(self):
            ...

        def test_b(self):
            ...

    @tag
    class TestMyClass2(ReferenceTestCase):
        def test_x(self):
            ...

        def test_y(self):
            ...

If run with ``python mytests.py --tagged``, only the tagged tests are
run (``TestMyClass1.test_a``, ``TestMyClass2.test_x`` and
``TestMyClass2.test_y``).

Regeneration of Results
~~~~~~~~~~~~~~~~~~~~~~~

When its main is run with ``--write-all`` or ``--write`` (or ``-W`` or ``-w``
respectively), it causes the framework to regenerate reference data
files. Different kinds of reference results can be regenerated by
passing in a comma-separated list of ``kind`` names immediately after
the ``--write`` option. If no list of ``kind`` names is provided, then all
test results will be regenerated.

To regenerate all reference results (or generate them for the first time)

.. code-block:: bash

   pytest -s --write-all

To regenerate just a particular kind of reference (e.g. table results)

.. code-block:: bash

    python my_tests.py --write table

To regenerate a number of different kinds of reference (e.g. both table
and graph results)

.. code-block:: bash

    python my_tests.py --write table graph

``unittest`` Integration Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

import os
import sys
import unittest

from tdda.referencetest.referencetest import ReferenceTest, tag


class ReferenceTestCase(unittest.TestCase, ReferenceTest):
    """
    Wrapper around the
    :py:class:`~tdda.referencetest.referencetest.ReferenceTest`
    class to allow it to operate as a test-case class using the
    ``unittest`` testing framework.

    The ``ReferenceTestCase`` class is a mix-in of
    :py:class:`unittest.TestCase`
    and :py:class:`~tdda.referencetest.referencetest.ReferenceTest`,
    so it can be used as the base class for unit tests, allowing the
    tests to use any of the standard ``unittest`` *assert* methods,
    and also use any of the ``referencetest`` *assert* extensions.
    """
    tag = tag

    def __init__(self, *args, **kwargs):
        # Initializer for a ReferenceTestCase instance.
        # This is called automatically by the ``unittest`` runtime framework.
        unittest.TestCase.__init__(self, *args, **kwargs)
        ReferenceTest.__init__(self, self.assertTrue)

    @staticmethod
    def main(module=None, argv=None, testtdda=False, **kw):
        """
        Wrapper around the :py:func:`unittest.main()` entry point.

        This is the same as the :py:func:`~tdda.referencetestcase.main()`
        function, and is provided just as a convenience, as it means that
        tests using the ``ReferenceTestCase`` class only need to import
        that single class on its own.
        """
        argv, tagged, check = _set_flags_from_argv(argv)
        if testtdda:
            saved = os.environ.get('TDDA_NO_CONFIG')
            os.environ['TDDA_NO_CONFIG'] = '1'
        try:
            _run_tests(module=module, argv=argv, tagged=tagged, check=check,
                       **kw)
        finally:
            if testtdda:
                if saved is not None:
                    os.environ['TDDA_NO_CONFIG'] = saved


def _run_tests(module=None, argv=None, tagged=False, check=False, **kw):
    """
    Run tests
    """
    if argv is None:
        argv = sys.argv
    loader = (TaggedTestLoader(check) if tagged or check
              else unittest.defaultTestLoader)
    if module is None:
        unittest.main(argv=argv, testLoader=loader, **kw)
    else:
        unittest.main(module=module, argv=argv, testLoader=loader, **kw)


def _set_flags_from_argv(argv=None):
    """
    This is used to set the class's write flag if a **-write** or
    **--write-all** (or **-W** or **-w**) option is passed on the
    command line, either using the argv provided,
    or :py:data:`sys.argv` otherwise.

    The **-write-all** (or **-W**) option takes no parameters, and turns on
    reference-regeneration for all kinds of results.

    The **-write** (or **-w**) option takes a list of parameter, consisting
    of names of result kinds to be regenerated. The names can be separate
    parameters, or they can be a single comma-separated parameter.

    The framework reports on each file being regenerated, by default. Use
    The **-wquiet** option to make it rewrite files quietly.

    The **--wquiet** option causes files to be rewritten silently.

    If the **-1** or **--tagged** option is set, then only run tagged tests.

    If the **-0** or **--check** option is set, then only report tagged tests,
    without running them.

    A tuple is returned, containing ``argv`` or :py:data:`sys.argv`, with
    any of the *rewrite*, *tagged* or *check* options options removed,
    plus the *tagged* and *checked* state.
    """
    if argv is None:
        argv = sys.argv
    rest = argv[1:]
    tagged = False
    check = False
    regenerate = False

    for i, arg in enumerate(rest):
        if arg.startswith('-') and not arg.startswith('--'):
            for flag in arg[1:]:
                if flag == 'W':
                    regenerate = True
                    arg = arg.replace('W', '')
                elif flag == '1':
                    tagged = True
                    arg = arg.replace('1', '')
                elif flag == '0':
                    check = True
                    arg = arg.replace('0', '')
            rest[i] = '' if arg == '-' else arg
        else:
            break
    rest = [a for a in rest if a]

    for quietflag in ('-wquiet', '--wquiet'):
        if quietflag in rest:
            idx = rest.index(quietflag)
            ReferenceTestCase.set_defaults(verbose=False)
            rest = rest[:idx] + rest[idx+1:]

    for writeflag in ('--W', '--write-all'):
        if writeflag in rest:
            idx = rest.index(writeflag)
            if idx:
                regenerate = True
                rest = rest[:idx] + rest[idx+1:]
                break

    for writeflag in ('-w', '--w', '--write'):
        if writeflag in rest:
            idx = rest.index(writeflag)
            if idx:
                if idx < len(rest) - 1:
                    for r in rest[idx+1:]:
                        for kind in r.split(','):
                            ReferenceTestCase.set_regeneration(kind)
                else:
                    raise Exception('--write option requires parameters; '
                                    'use --write-all to regenerate all '
                                    'reference results')
            rest = rest[:idx]
            break

    for option in ('--tagged', '--istagged'):
        if option in rest:
            idx = rest.index(option)
            if idx:
                rest = rest[:idx] + rest[idx+1:]
                if option in ('-0', '--istagged'):
                    check = True
                else:
                    tagged = True

    if regenerate:
        ReferenceTestCase.set_regeneration()
    return (argv[:1] + rest, tagged, check)


class TaggedTestLoader(unittest.TestLoader):
    """
    Subclass of ``TestLoader``, which strips out any non-tagged tests.
    """
    def __init__(self, check, printer=None):
        unittest.TestLoader.__init__(self)
        self.check = check
        self.print = printer or print

    def loadTestsFromTestCase(self, *args, **kwargs):
        suite = unittest.TestLoader.loadTestsFromTestCase(self, *args,
                                                          **kwargs)
        return self._tagged_tests_only(suite)

    def loadTestsFromModule(self, *args, **kwargs):
        suite = unittest.TestLoader.loadTestsFromModule(self, *args, **kwargs)
        return self._tagged_tests_only(suite)

    def loadTestsFromName(self, *args, **kwargs):
        suite = unittest.TestLoader.loadTestsFromName(self, *args, **kwargs)
        return self._tagged_tests_only(suite)

    def loadTestsFromNames(self, *args, **kwargs):
        suite = unittest.TestLoader.loadTestsFromNames(self, *args, **kwargs)
        return self._tagged_tests_only(suite)

    def _tagged_tests_only(self, suite):
        newsuite = unittest.TestSuite()
        cases = set()
        for test in suite:
            if isinstance(test, unittest.suite.TestSuite):
                test = self._tagged_tests_only(test)
            if self.check and not isinstance(test, unittest.suite.TestSuite):
                cases.add('%s.%s' % (test.__class__.__module__,
                                     test.__class__.__name__))
            else:
                newsuite.addTest(test)
        if self.check:
            for module in cases:
                self.print(module)
        return newsuite

    def getTestCaseNames(self, testCaseClass):
        names = unittest.TestLoader.getTestCaseNames(self, testCaseClass)
        if hasattr(testCaseClass, '_tagged'):
            return names
        else:
            return [name for name in names
                         if hasattr(getattr(testCaseClass, name), '_tagged')]


def main():
    """
    Wrapper around the :py:func:`unittest.main()` entry point.
    """
    ReferenceTestCase.main()

