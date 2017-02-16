"""

The :py:mod:`~tdda.referencetest` module provides support for unit tests,
allowing them to easily compare test results against saved
"known to be correct" reference results.

This is typically useful for testing software that produces any of the following
types of output:

    - a CSV file
    - a text file (for example: HTML, JSON, logfiles, graphs, tables, etc)
    - a string
    - a Pandas DataFrame.

The main features are:

    - If the comparison between a string and a file fails,
      the actual string is written to a file and a ``diff``
      command is suggested for seeing the differences between
      the actual output and the expected output.

    - There is support for CSV files, allowing fine control over
      how the comparison is to be performed. This includes:

        - the ability to select which columns to compare (and which
          to exclude from the comparison).
        - the ability to compare metadata (types of fields) as well
          as values.
        - the ability to specify the precision (as number of decimal places)
          for the comparison of floating-point values.
        - clear reporting of where the differences lie, if the comparison
          should fail.

    - There is support for ignoring lines within the strings/files
      that contain particular patterns or regular expressions.
      This is typically useful for filtering out things like
      version numbers and timestamps that vary in the output
      from run to run, but which do not indicate a problem.

    - There is support for re-writing the reference output
      with the actual output. This, obviously, should be used
      only after careful checking that the new output is correct,
      either because the previous output was in fact wrong,
      or because the intended behaviour has changed.

The module provides interfaces for this to be called from unit-tests
based on either the standard Python ``unittest`` framework, or on ``pytest``.


**Simple ``unittest`` example:**

For use with ``unittest``, the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` API is provided
through the :py:class:`~tdda.referencetest.referencetestcase.ReferenceTestCase`
class. This is an extension to the standard :py:class:`unittest.TestCase`
class, so that the ``ReferenceTest`` methods can be called directly from
``unittest`` tests.

This example shows how to write a test for a function that generates
a CSV file::

    from tdda.referencetest.referencetestcase import ReferenceTestCase
    import my_module

    class MyTest(ReferenceTestCase):
        def test_my_csv_file(self):
            result = my_module.produce_a_csv_file(self.tmp_dir)
            self.assertCSVFileCorrect(result, 'result.csv')

    MyTest.set_default_data_location('testdata')

    if __name__ == '__main__':
        ReferenceTestCase.main()

The first time you run the test, it will fail because the reference test
results do not exist yet. You can create the reference results automatically::

    python mytest.py --write-all

Having generated the reference results, you should examine the files it has
produced in the data output location, to check that they are as expected.
Once you're happy that they are correct, then you have a unit-test that you
can rerun as often as you like to check for regressions::

    python mytest.py


**Simple ``pytest`` example:**


For use with ``pytest``, the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` API is provided
through the :py:mod:`~tdda.referencetest.referencepytest` module. This is
a module that can be imported directly from ``pytest`` tests, allowing them
to call ``ReferenceTest`` methods as though they were functions.

This example shows how to write a test for a function that generates
a CSV file::

    from tdda.referencetest import referencepytest
    import my_module

    def test_my_csv_function(ref):
        resultfile = my_module.produce_a_csv_file(self.tmp_dir)
        ref.assertCSVFileCorrect(resultfile, 'result.csv')

    referencepytest.set_default_data_location('testdata')

You also need a ``conftest.py`` file, to define the fixtures and defaults::

    import pytest
    from tdda.referencetest import referencepytest

    def pytest_addoption(parser):
        referencepytest.addoption(parser)

    @pytest.fixture(scope='module')
    def ref(request):
        return referencepytest.ref(request)

    referencepytest.set_default_data_location('testdata')

The first time you run the test, it will fail because the reference test
results do not exist yet. You can create the reference results automatically::

    pytest --write-all -s

Having generated the reference results, you should examine the files it has
produced in the data output location, to check that they are as expected.
Once you're happy that they are correct, then you have a unit-test that you
can rerun as often as you like to check for regressions::

    pytest


Prerequisites
-------------

    - :py:mod:`pandas` (required for CSV file support)

This can be installed with::

    pip install pandas

"""

from tdda.referencetest.referencetestcase import ReferenceTestCase
