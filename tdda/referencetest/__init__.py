"""The :py:mod:`~tdda.referencetest` module provides support for unit tests,
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
        - clear reporting of where the differences are, if the comparison
          fails.

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

    - It allows you to group your reference results into different *kinds*.
      This means you can keep different kinds of reference result files in
      different locations. It also means that you can selectively
      choose to only regenerate particular kinds of reference results,
      if they need to be updated because they turned out to have been
      wrong or if the intended behaviour has changed.
      Kinds are strings.

Prerequisites
-------------

 - :py:mod:`pandas` optional, required for CSV file support, see https://pandas.pydata.org.
 - :py:mod:`pytest` optional, required for tests based on pytest rather than ``unittest``, see https://docs.pytest.org.

These can be installed with::

    pip install pandas
    pip install pytest

The module provides interfaces for this to be called from unit-tests
based on either the standard Python :py:mod:`unittest` framework,
or on :py:mod:`pytest`.


Simple Examples
---------------

**Simple unittest example:**

For use with :py:mod:`unittest`, the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` API is provided
through the :py:class:`~tdda.referencetest.referencetestcase.ReferenceTestCase`
class. This is an extension to the standard :py:class:`unittest.TestCase`
class, so that the ``ReferenceTest`` methods can be called directly from
:py:mod:`unittest` tests.

This example shows how to write a test for a function that generates
a CSV file::

    from tdda.referencetest import ReferenceTestCase, tag
    import my_module

    class MyTest(ReferenceTestCase):
        @tag
        def test_my_csv_file(self):
            result = my_module.produce_a_csv_file(self.tmp_dir)
            self.assertCSVFileCorrect(result, 'result.csv')

    MyTest.set_default_data_location('testdata')

    if __name__ == '__main__':
        ReferenceTestCase.main()

To run the test:

.. code-block:: bash

    python mytest.py

The test is tagged with ``@tag``, meaning that it will be included if
you run the tests with the ``--tagged`` option flag to specify that only
tagged tests should be run:

.. code-block:: bash

    python mytest.py --tagged

The first time you run the test, it will produce an error unless you
have already created the expected ("reference") results. You can
create the reference results automatically

.. code-block:: bash

    python mytest.py --write-all

Having generated the reference results, you should carefully examine
the files it has produced in the data output location, to check that
they are as expected.


**Simple pytest example:**


For use with :py:mod:`pytest`, the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` API is provided
through the :py:mod:`~tdda.referencetest.referencepytest` module. This is
a module that can be imported directly from ``pytest`` tests, allowing them
to access :py:class:`~tdda.referencetest.referencetest.ReferenceTest`
methods and properties.

This example shows how to write a test for a function that generates
a CSV file::

    from tdda.referencetest import referencepytest, tag
    import my_module

    @tag
    def test_my_csv_function(ref):
        resultfile = my_module.produce_a_csv_file(ref.tmp_dir)
        ref.assertCSVFileCorrect(resultfile, 'result.csv')

    referencepytest.set_default_data_location('testdata')

You also need a ``conftest.py`` file, to define the fixtures and defaults::

    import pytest
    from tdda.referencetest import referencepytest

    def pytest_addoption(parser):
        referencepytest.addoption(parser)

    def pytest_collection_modifyitems(session, config, items):
        referencepytest.tagged(config, items)

    @pytest.fixture(scope='module')
    def ref(request):
        return referencepytest.ref(request)

    referencepytest.set_default_data_location('testdata')

To run the test:

.. code-block:: bash

    pytest

The test is tagged with ``@tag``, meaning that it will be included if
you run the tests with the ``--tagged`` option flag to specify that only
tagged tests should be run:

.. code-block:: bash

    pytest --tagged

The first time you run the test, it will produce an error unless you
have already created the expected ("reference") results. You can
create the reference results automatically:

.. code-block:: bash

    pytest --write-all -s

Having generated the reference results, you should examine the files it has
produced in the data output location, to check that they are as expected.

"""

from tdda.referencetest.referencetest import tag
from tdda.referencetest.referencetestcase import (ReferenceTestCase,
                                                  TaggedTestLoader)
from tdda.referencetest.captureoutput import CaptureOutput
