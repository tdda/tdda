# -*- coding: utf-8 -*-
"""
writabletestcase.py: extended test methods for test-driven data analysis.

This interface has now been superseded by the newer, more featureful,
tdda.referencetest implementation, in the 'refererencetest' subdirectory.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2022
"""

import os
import shutil
import sys
import tempfile
import unittest

from unittest import main

__version__ = '0.0.4'

# DEFAULT_FAIL_DIR is the default location for writing failing output
# if calls to check_string_against_file fail.
#
# There are several ways to control this:
#
# 1. check_string_against_file takes a faildir parameter; this is used
#    if provided.
#
# 2. There is a class method, set_defaults, which can be called
#    (with WritableTestCase.set_defaults(faildir=...) to override
#    this variable.
#
# 3. Failing that, as below, if the environment variable TDDA_FAIL_DIR
#    is set to a location, that will be used.
#
# 4. Finally, it defaults to /tmp, c:\temp or whatever tempfile.gettempdir()
#    returns, as appropriate.
#

DEFAULT_FAIL_DIR = os.environ.get('TDDA_FAIL_DIR', tempfile.gettempdir())

def check_strings(actual, expected, actual_path, expected_path,
                  ignore_patterns, lstrip=False, rstrip=False):
    """
    Compare two lists of strings (actual and expected), one-by-one.

    ignore_ patterns    is an optional list of substrings; lines containing
                        these substrings will be ignored in the comparison.

    actual_path         is the path to which the actual string will be written
                        if the check fails.

    expected_path       is the path from which expected was read; it iss used
                        to suggest a diff command to use on files for
                        strings failing the check.

    lstrip              if set to true, both strings are left stripped before
                        the comparison is carried out.
                        Note: the stripping on a per-line basis.

    rstrip              if set to true, both strings are right stripped before
                        the comparison is carried out.
                        Note: the stripping on a per-line basis.

    Returns 1 if there were any differences, and 0 otherwise.
    """
    failures = 0
    normalize = normalize_function(lstrip, rstrip)
    if len(actual) == len(expected):
        diffs = [i for i in range(len(actual))
                 if normalize(actual[i]) != normalize(expected[i])]

        if diffs:
            ignore_patterns = ignore_patterns or []
            for i in diffs:
                failures = 1
                for pattern in ignore_patterns:
                    if pattern in actual[i]:
                        failures = 0
                        break
                if failures > 0:
                    break
    else:
        failures = 1
    if failures > 0:
        report_failure(actual_path, expected_path, ignore_patterns)
    return failures


def normalize_function(left, right):
    """
    Return the appropriate function for stripping a string,
    with left and right being booleans that specify whether
    to strip on the two sides.
    """
    if left and right:
        return lambda s: s.strip()
    elif left:
        return lambda s: s.lstrip()
    elif right:
        return lambda s: s.trstrip()
    else:
        return lambda s: s


def report_failure(actual_path, expected_path, ignore_patterns):
    """
    Reports a failure by suggesting a diff command between the actual
    and expected files. Also notes any exclusions in the comparison.
    """
    print('\nFile check failed.')
    print('Compare with "diff %s %s".\n' % (actual_path, expected_path)
    if ignore_patterns:
        print('Note exclusions:')
        for pattern in ignore_patterns:
            print(pattern)


def write_output(path, result, verbose=True):
    """
    Writes the result given to the path provided.

    If verbose is set, this is also reported.
    """
    with open(path, 'w') as f:
        f.write(result)
    if verbose:
        print('Expected file %s written.' % path)


def set_write_from_argv(argv=None):
    """
    This is used to set the class's write flag if a -w option
    is passed on the command line, either using the argv provided,
    or sys.argv otherwise.

    argv or sys.argv is returned, with any '-w' removed.

    Canonical usage is to add the following to the end of a test file:

    if __name__ == '__main__':
        unittest.main(argv=writabletestcase.set_write_from_argv())
    """
    if argv is None:
        argv = sys.argv
    if '-w' in argv:
        WritableTestCase.set_defaults(write=True)
        idx = argv.index('-w')
        return argv[:idx] + argv[idx+1:]
    else:
        return argv


class WritableTestCase(unittest.TestCase):
    """
    WritableTestCase is a subclass of, and drop-in replacement
    for unittest.TestCase. It extends the class by adding two
    main methods, for checking strings against reference files.

    This is typically useful when software produces either
    a (text) file or a string as output.

    The main features are:

        - If the comparison between a string and a file fails,
          the actual string is written to a file and a diff
          command is suggested for seeing the differences between
          the actual output and the expected output.

        - There is support for ignoring lines within the strings/files
          that contain particular patterns.
          This is typically useful for filtering out things like
          version numbers and timestamps that vary in the output
          from run to run, but which do not indicate a problem.

        - There is support for re-writing the reference output
          with the actual output. This, obviously, should be used
          only after careful checking that the new output is correct,
          either because the previous output was in fact wrong,
          or because the intended behaviour has changed.
    """

    write = False
    faildir = DEFAULT_FAIL_DIR

    def __init__(self, *args, **kwargs):
        """
        Initialize class and super.
        """
        unittest.TestCase.__init__(self, *args, **kwargs)

    @classmethod
    def set_defaults(cls, write=None, faildir=None):
        """
        Class method used to specify test behaviour:

            - if write is set to True, all reference files used
              for testing are replaced with the actual output
              passed to the tests, whether these are provided
              as strings or files.

            - faildir specifies the location for writing actual
              output when string-based comparisons against
              reference files fail.
        """
        if write is not None:
            cls.write = write
        if faildir is not None:
            cls.faildir = faildir

    def check_file(self, actual_path, expected_path,
                   ignore_patterns=None, lstrip=False, rstrip=False,
                   do_assert=True):
        """
        Check a pair of files, line by line, with optional
        ignore patterns (substrings) and optionally left-
        and/or right-stripping the contents of both files.

        Normally, this finishes by performing the assertion,
        but if do_assert is set to False, this is omitted.
        In either case, True is returned for success, and False
        for failure (though, of course, in the case of failure,
        there will be no return if do_assert is True).
        """
        try:
            with open(expected_path) as f:
                expected = f.readlines()
        except IOError:
            expected = []
            print('Reference file %s not found.' % expected_path)
            raise
        if self.write:
            shutil.copyfile(actual_path, expected_path)
            return 0
        try:
            with open(actual_path) as f:
                actual = f.readlines()
        except IOError:
            print('Actual file %s not found.' % actual_path)
            raise
        if rstrip and actual and len(actual[-1]) == 0:
            actual = actual[:-1]
        failures = check_strings(actual, expected, actual_path, expected_path,
                                 ignore_patterns, lstrip=lstrip, rstrip=rstrip)
        if do_assert:
            self.assertEqual(failures, 0)
        return failures

    def check_string_against_file(self, actualString, expected_path,
                                  ignore_patterns=None, lstrip=False,
                                  rstrip=False, faildir=None,
                                  do_assert=True):
        """
        Check a string against expected content in a file,
        line by line, with optional ignore patterns (substrings)
        and optionally left- and/or right-stripping the contents
        of both files.

        Normally, this finishes by performing the assertion,
        but if do_assert is set to False, this is omitted.
        In either case, True is returned for success, and False
        for failure (though, of course, in the case of failure,
        there will be no return if do_assert is True).
        """
        if self.write:
            write_output(expected_path, actualString)
        try:
            with open(expected_path) as f:
                expectedString = f.read()
        except IOError:
            expectedString = ''
        if expectedString == actualString:
            self.assertEqual(expectedString, actualString)
            return 0

        filename = os.path.split(expected_path)[1]
        actual_path = os.path.join(faildir or self.faildir, filename)
        try:
            with open(actual_path, 'w') as f:
                f.write(actualString)
        except IOError:
            print('Failed to write actual string to %s.' % actual_path,
                  file=sys.stderr)
        failures = check_strings(actualString.splitlines(),
                                 expectedString.splitlines(),
                                 actual_path, expected_path,
                                 ignore_patterns=ignore_patterns,
                                 lstrip=lstrip, rstrip=rstrip)
        if do_assert:
            self.assertEqual(failures, 0)
        return failures


if __name__ == '__main__':
    main(sys.argv)
