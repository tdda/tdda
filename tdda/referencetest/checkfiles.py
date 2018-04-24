# -*- coding: utf-8 -*-

"""
checkfiles.py: comparison mechanism for text files

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2018
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
# from __future__ import unicode_literals

import os
import re
import sys
import tempfile

from tdda.referencetest.basecomparison import BaseComparison, copycmd


class FilesComparison(BaseComparison):

    def check_strings(self, actual, expected,
                      actual_path=None, expected_path=None,
                      lstrip=False, rstrip=False,
                      ignore_substrings=None, ignore_patterns=None,
                      ignore_lines=None,
                      preprocess=None, max_permutation_cases=0, msgs=None):
        """
        Compare two lists of strings (actual and expected), one-by-one.

            *actual*
                                is a list of strings.
            *expected*
                                is the expected list of strings.
            *actual_path*
                                is the path of the file where the actual
                                string originated (used for reporting errors).
            *expected_path*
                                is the path from which expected was read; it is
                                used to suggest a diff command to use on files
                                for strings failing the check.
            *lstrip*
                                if set to true, both strings are left-stripped
                                before the comparison is carried out.
                                Note: the stripping on a per-line basis.
            *rstrip*
                                if set to true, both strings are right-stripped
                                before the comparison is carried out.
                                Note: the stripping on a per-line basis.
            *ignore_substrings*
                                is an optional list of substrings; lines
                                containing any of these substrings will be
                                ignored in the comparison.
            *ignore_patterns*
                                is an optional list of regular expressions;
                                lines will be considered to be the same if
                                they only differ in substrings that match one
                                of these regular expressions. The expressions
                                must not contain parenthesised groups, and
                                should only include explicit anchors if they
                                need refer to the whole line.
            *ignore_lines*
                                is an optional list of substrings; lines
                                containing any of these substrings will be
                                completely removed before carrying out the
                                comparison. This is the means by which you
                                would exclude 'optional' content.
            *preprocess*
                                is an optional function that takes a list of
                                strings and preprocesses it in some way; this
                                function will be applied to both the actual
                                and expected.
            *max_permutation_cases*
                                is an optional number specifying the maximum
                                number of permutations allowed; if the actual
                                and expected lists differ only in that their
                                lines are permutations of each other, and
                                the number of such permutations does not
                                exceed this limit, then the two are considered
                                to be identical.
            *msgs*
                                is an optional list, where information about
                                differences will be appended; if not specified,
                                a new list will be created and returned.

        Returns a tuple (failures, msgs), where failures is 1 if the lists
        differ and 0 if they are the same. The returned msgs is a list
        containing information about how they differed.
        """

        if msgs is None:
            msgs = []
        first_error = None
        failure_cases = []

        if preprocess:
            expected = preprocess(expected)
            actual = preprocess(actual)

        if actual and len(actual[-1]) == 0:
            actual = actual[:-1]
        if expected and len(expected[-1]) == 0:
            expected = expected[:-1]

        if ignore_lines:
            actual = [a for a in actual
                      if not any(i in a for i in ignore_lines)]
            expected = [a for a in expected
                        if not any(i in a for i in ignore_lines)]

        if len(actual) == len(expected):
            normalize = self.normalize_function(lstrip, rstrip)
            diffs = [i for i in range(len(actual))
                     if normalize(actual[i]) != normalize(expected[i])]
            ndiffs = len(diffs)
            if ndiffs > 0:
                ignore_substrings = ignore_substrings or []
                ignore_patterns = ignore_patterns or []
                anchored_patterns = [('' if p.startswith('^') else '^(.*)')
                                      + p
                                      + ('' if p.endswith('$') else '(.*)$')
                                     for p in ignore_patterns]
                cPatterns = [re.compile(p) for p in anchored_patterns]
                if any(cp.groups > 3 for cp in cPatterns):
                    raise Exception('Invalid patterns: %s' % ignore_patterns)
                for i in diffs:
                    for pattern in ignore_substrings:
                        if pattern in actual[i] or pattern in expected[i]:
                            break
                    else:
                        # not an ignorable substring line, so try patterns
                        for pattern in cPatterns:
                            mExpected = re.match(pattern, expected[i])
                            if mExpected:
                                mActual = re.match(pattern, actual[i])
                                if not mActual:
                                    continue
                                if pattern.groups < 3:
                                    # matched an anchored expression
                                    break
                                lhs = mActual.group(1) + mActual.group(3)
                                rhs = (mExpected.group(1)
                                       + mExpected.group(3))
                                if lhs == rhs:
                                    actual[i] = (mActual.group(1) + '...'
                                                 + mActual.group(3))
                                    expected[i] = (mExpected.group(1)
                                                   + '...'
                                                   + mExpected.group(3))
                                    break
                        else:
                            # difference can't be ignored
                            if first_error is None:
                                first_error = (
                                    '%d line%s different, starting at line'
                                    ' %d'
                                    % (ndiffs,
                                       's are' if ndiffs != 1
                                               else ' is', i+1))
                            if len(failure_cases) < max_permutation_cases:
                                failure_cases.append((i,
                                                      actual[i],
                                                      expected[i]))
                            else:
                                break
                    # ignored a line, so there is one fewer to report
                    ndiffs -= 1
        else:
            ndiffs = max_permutation_cases + 1
            first_error = ('%s have different numbers of lines'
                           % ('Files' if actual_path else 'Strings'))

        if ndiffs > 0 and ndiffs <= max_permutation_cases:
            ndiffs = self.check_for_permutation_failures(failure_cases)
        if ndiffs > 0:
            if first_error:
                self.info(msgs, first_error)
            self.add_failures(msgs, actual_path, expected_path,
                              ignore_substrings=ignore_substrings,
                              ignore_patterns=ignore_patterns,
                              preprocess=preprocess, actual=actual,
                              expected=expected)
        return (1 if ndiffs > 0 else 0, msgs)

    def check_string_against_file(self, actual, expected_path,
                                  actual_path=None,
                                  lstrip=False, rstrip=False,
                                  ignore_substrings=None,
                                  ignore_patterns=None,
                                  ignore_lines=None,
                                  preprocess=None, max_permutation_cases=0,
                                  msgs=None):
        """
        Check a string (or list of strings) against the contents of a
        reference file.

        This is a wrapper around check_strings(), where the 'expected'
        strings are read from a file rather than being passed in explicitly.

        Other parameters are the same as for py:meth:`check_strings()`.

        The actual_path parameter is the pathname of the file that the
        actual string originally came from (if it came from a file at all;
        if not, it should be None).
        """
        if msgs is None:
            msgs = []
        try:
            with open(expected_path) as f:
                content = f.read()
                expected_ends_with_newline = content.endswith('\n')
                expected = content.splitlines()
        except IOError:
            self.info(msgs, 'Reference file %s not found.' % expected_path)
            self.add_failures(msgs, None, expected_path, actual=actual)
            return (1, msgs)

        if type(actual) in (list, tuple):
            actuals = actual
            actual_ends_with_newline = expected_ends_with_newline
        else:
            actuals = actual.splitlines()
            actual_ends_with_newline = actual.endswith('\n')
        (code, msgs) = self.check_strings(actuals, expected,
                                          actual_path=actual_path,
                                          expected_path=expected_path,
                                          lstrip=lstrip, rstrip=rstrip,
                                          ignore_substrings=ignore_substrings,
                                          ignore_patterns=ignore_patterns,
                                          ignore_lines=ignore_lines,
                                          preprocess=preprocess,
                                          max_permutation_cases=
                                              max_permutation_cases,
                                          msgs=msgs)
        #if expected_ends_with_newline != actual_ends_with_newline:
        #    code = 1
        #    if actual_ends_with_newline:
        #        self.info(msgs, 'Actual string has unexpected newline at end')
        #    else:
        #        self.info(msgs, 'Actual string is missing newline at end')
        return (code, msgs)

    def check_file(self, actual_path, expected_path,
                   lstrip=False, rstrip=False,
                   ignore_substrings=None, ignore_patterns=None,
                   ignore_lines=None,
                   preprocess=None, max_permutation_cases=0, msgs=None):
        """
        Check a pair of files, line by line, with optional
        ignore patterns (substrings) and optionally left-
        and/or right-stripping the contents of both files.

        This is a wrapper around check_strings(), where both the 'actual'
        and 'expected' strings are read from files rather than being passed
        in explicitly.

        Other parameters are the same as for :py:meth:`check_strings()`.

        """
        if msgs is None:
            msgs = []
        try:
            with open(expected_path) as f:
                content = f.read()
                expected_ends_with_newline = content.endswith('\n')
                expected = content.splitlines()
        except IOError:
            self.info(msgs, 'Reference file %s not found.' % expected_path)
            self.info(msgs,
                      'Initialize from actual content with:\n    %s %s %s'
                      % (copycmd(), actual_path, expected_path))
            return (1, msgs)
        try:
            with open(actual_path) as f:
                content = f.read()
                actual_ends_with_newline = content.endswith('\n')
                actuals = content.splitlines()
        except IOError:
            self.info(msgs, 'Actual file %s not found.'
                            % os.path.normpath(actual_path))
            self.add_failures(msgs, actual_path, expected_path)
            return (1, msgs)
        (code, msgs) = self.check_strings(actuals, expected,
                                          actual_path=actual_path,
                                          expected_path=expected_path,
                                          lstrip=lstrip, rstrip=rstrip,
                                          ignore_substrings=ignore_substrings,
                                          ignore_patterns=ignore_patterns,
                                          ignore_lines=ignore_lines,
                                          preprocess=preprocess,
                                          max_permutation_cases=
                                              max_permutation_cases,
                                          msgs=msgs)
        #if expected_ends_with_newline != actual_ends_with_newline:
        #    code = 1
        #    if actual_ends_with_newline:
        #        self.info(msgs, 'Actual string has unexpected newline at end')
        #    else:
        #        self.info(msgs, 'Actual string is missing newline at end')
        return (code, msgs)

    def check_files(self, actual_paths, expected_paths,
                    lstrip=False, rstrip=False,
                    ignore_substrings=None, ignore_patterns=None,
                    ignore_lines=None,
                    preprocess=None, max_permutation_cases=0, msgs=None):
        """
        Compare a list of files against a list of reference files.

        It compares all the files pair-wise from the two lists, and then
        reports on any differences. This is different from calling
        check_file() separately for each pair, which will stop as soon
        as the first difference is found.

        Other parameters are the same as for :py:meth:`check_strings()`.

        """
        failures = 0
        if msgs is None:
            msgs = []
        for (actual_path, expected_path) in zip(actual_paths, expected_paths):
            try:
                r = self.check_file(actual_path, expected_path,
                                    ignore_substrings=ignore_substrings,
                                    ignore_patterns=ignore_patterns,
                                    ignore_lines=ignore_lines,
                                    preprocess=preprocess,
                                    lstrip=lstrip, rstrip=rstrip,
                                    max_permutation_cases=max_permutation_cases,
                                    msgs=msgs)
                (n, msgs) = r
                failures += n
            except Exception as e:
                self.info(msgs, 'Error comparing %s and %s (%s %s)'
                                % (os.path.normpath(actual_path),
                                   expected_path,
                                   e.__class__.__name__, str(e)))
                failures += 1
        return (failures, msgs)

    def check_for_permutation_failures(self, failure_cases):
        """
        Check a collection of actual/reference comparison lines, to
        see if they are different only because one is a permutation of
        the other.
        """
        actuals = [f[1] for f in failure_cases]
        expecteds = [f[2] for f in failure_cases]
        if self.verbose and self.print_fn:
            self.print_fn('W(%s)' %len(actuals), file=sys.stderr)
        if sorted(actuals) == sorted(expecteds):
            return 0
        else:
            return len(actuals)

    def normalize_function(self, left, right):
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
            return lambda s: s.rstrip()
        else:
            return lambda s: s

    def add_failures(self, msgs, actual_path, expected_path,
                     ignore_substrings=None, ignore_patterns=None,
                     preprocess=None, actual=None, expected=None):
        """
        Build a list of messages describing the way in which two files are
        different.
        """
        if actual_path and expected_path:
            self.info(msgs, self.compare_with(os.path.normpath(actual_path),
                                              expected_path))
        elif expected_path:
            self.info(msgs, 'Expected file %s' % expected_path)
        elif actual_path:
            self.info(msgs, 'Actual file %s' % os.path.normpath(actual_path))
        else:
            self.info(msgs, 'No files')
        if ignore_substrings or ignore_patterns:
            self.info(msgs, 'Note exclusions:')
        if ignore_substrings:
            for pattern in ignore_substrings:
                self.info(msgs, '    ' + pattern)
        if ignore_patterns:
            for pattern in ignore_patterns:
                self.info(msgs, '    ' + pattern)
        if preprocess and actual_path:
            actualFilename = os.path.split(actual_path)[1]
            modifiedActual = os.path.join(self.tmp_dir,
                                          'actual-' + actualFilename)
            modifiedRef = os.path.join(self.tmp_dir,
                                       'expected-' + actualFilename)
            with open(modifiedActual, 'w') as f:
                f.write(actual if type(actual) == str
                        else '\n'.join(actual))
            with open(modifiedRef, 'w') as f:
                f.write('\n'.join(expected))
            self.info(msgs, self.compare_with(modifiedActual, modifiedRef,
                                              qualifier='preprocessed'))
        elif expected_path and not actual_path:
            expectedFilename = os.path.split(expected_path)[1]
            tmpActualFilename = os.path.join(self.tmp_dir,
                                            'actual-' + expectedFilename)
            with open(tmpActualFilename, 'w') as f:
                f.write(actual if type(actual) == str
                        else '\n'.join(actual))
            self.info(msgs,
                      self.compare_with(tmpActualFilename, expected_path))

