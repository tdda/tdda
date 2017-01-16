"""
Reference testing for test-driven data analysis.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016

Support for comparing test results against saved "known to be correct"
reference results.

This is typically useful when software produces either a (text or csv)
file or a string as output.

The main features are:

    - If the comparison between a string and a file fails,
      the actual string is written to a file and a diff
      command is suggested for seeing the differences between
      the actual output and the expected output.

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

For details of the unittest interface:

    >>> import tdda.referencetest.referencetestcase
    >>> help(tdda.referencetest.refererencetestcase)

For details of the pytest interface:

    >>> import tdda.referencetest.referencepytest
    >>> help(tdda.referencetest.refererencepytest)

"""

from tdda.referencetest.referencetestcase import ReferenceTestCase
