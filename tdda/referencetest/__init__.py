"""

The :py:mod:`~tdda.referencetest` module provides support for unit tests,
allowing them to easily compare test results against saved
"known to be correct" reference results.

This is typically useful when software produces either a (text or CSV)
file or a string as output.

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
based on either the standard python unittest framework, or on pytest.

For use with ``unittest``, the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` API is provided
through the :py:class:`~tdda.referencetest.referencetestcase.ReferenceTestCase`
class. This is an extension to the standard :py:class:`unittest.TestCase`
class, so that the ``ReferenceTest`` methods can be called directly from
``unittest`` tests.

For use with ``pytest``, the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` API is provided
through the :py:mod:`~tdda.referencetest.referencepytest` module. This is
a module that can be imported directly from ``pytest`` tests, allowing them
to call ``ReferenceTest`` methods as though they were functions.

"""

from tdda.referencetest.referencetestcase import ReferenceTestCase
