"""
Reference testing for test-driven data analysis.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016

Support for comparing test results against saved "known to be correct"
reference results.

This is typically useful when software produces either a (text or CSV)
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

For details of the API:

    >>> from tdda.referencetest import referencetest
    >>> help(referencetest)

For use with unittest, the referencetest API is provided as an extension
to the unittest.TestCase class, with methods that can be called directly
from unittest tests. For details of this unittest interface:

    >>> from tdda.referencetest import referencetestcase
    >>> help(referencetestcase)

For use with pytest, the referencetest API is provided as a set of functions
that can be called directly from pytest tests. For details of this pytest
interface:

    >>> from tdda.referencetest import referencepytest
    >>> help(referencepytest)

To copy the examples to your own 'referencetest-examples' directory:

    python -m tdda.referencetest.examples [mydirectory]

"""

from tdda.referencetest.referencetestcase import ReferenceTestCase
