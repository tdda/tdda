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
from collections import namedtuple

from tdda.referencetest.basecomparison import (BaseComparison, Diffs,
                                               Reconstruction, copycmd)


BinaryInfo = namedtuple('BinaryInfo',
                        ('byteoffset', 'actualLen', 'expectedLen'))


class FilesComparison(BaseComparison):

    def check_strings(self, actual, expected,
                      actual_path=None, expected_path=None,
                      lstrip=False, rstrip=False,
                      ignore_substrings=None, ignore_patterns=None,
                      remove_lines=None,
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
            *remove_lines*
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
                                is an optional Diffs object, where information
                                about differences will be appended; if not
                                specified, a new object will be created and
                                returned.

        Returns a tuple (failures, msgs), where failures is 1 if the lists
        differ and 0 if they are the same. The returned msgs is a list
        containing information about how they differed.
        """

        if msgs is None:
            msgs = Diffs()
        first_error = None
        first_error_line = None
        failure_cases = []
        reconstruction = None

        if preprocess:
            expected = preprocess(expected)
            actual = preprocess(actual)

        if actual and len(actual[-1]) == 0:
            actual = actual[:-1]
        if expected and len(expected[-1]) == 0:
            expected = expected[:-1]

        original_actual = actual
        original_expected = expected
        actual_map = {i: i for i in range(len(original_actual))}
        expected_map = {i: i for i in range(len(original_expected))}
        actual_removals = set()
        expected_removals = set()

        if remove_lines:
            actual_removals = set([i for i, a in enumerate(original_actual)
                                   if any(r in a for r in remove_lines)])
            expected_removals = set([i for i, a in enumerate(original_expected)
                                     if any(r in a for r in remove_lines)])
            actual = [a for i, a in enumerate(original_actual)
                      if i not in actual_removals]
            expected = [a for i, a in enumerate(original_expected)
                        if i not in expected_removals]

            # now build mappings from the after-removal line-numbers back to
            # the original line numbers, for both actual and expected
            iactual = 0
            for i in range(len(original_actual)):
                if i not in actual_removals:
                    actual_map[iactual] = i
                    iactual += 1
            iexpected = 0
            for i in range(len(original_expected)):
                if i not in expected_removals:
                    actual_map[iexpected] = i
                    iexpected += 1

        if len(actual) == len(expected):
            actual_ignored = set()
            expected_ignored = set()
            normalize = self.normalize_function(lstrip, rstrip)
            diffs = [i for i in range(len(actual))
                     if normalize(actual[i]) != normalize(expected[i])]
            ndiffs = len(diffs)

            if ndiffs > 0:
                ignore_substrings = ignore_substrings or []
                ignore_patterns = ignore_patterns or []
                anchored_patterns = [('' if p.startswith('^') else '^(.*)')
                                      + ('(%s)' % p)
                                      + ('' if p.endswith('$') else '(.*)$')
                                     for p in ignore_patterns]
                cPatterns = [re.compile(p) for p in anchored_patterns]
                if any(cp.groups > 3 for cp in cPatterns):
                    raise Exception('Invalid patterns: %s' % ignore_patterns)
                for i in diffs:
                    # 'i' is a line-number in the after-removals datasets
                    for substr in ignore_substrings:
                        if substr in actual[i] or substr in expected[i]:
                            # ignored a line, so there is one fewer to report
                            #
                            # TODO: This ignores a line even if it only
                            #       matches on ONE side and NOT on the other!
                            #       That doesn't seem right at all, but to
                            #       change 'or' to 'and' would change the
                            #       semantics in a way that will break some
                            #       tests in other software that is depending
                            #       on this behaviour. We should deprecate
                            #       this, and publish a timetable for changing
                            #       it.
                            ndiffs -= 1
                            actual_ignored.add(actual_map[i])
                            expected_ignored.add(expected_map[i])
                            break
                    else:
                        # not an ignorable substring line, so try patterns
                        if self.check_patterns(cPatterns, actual, expected, i):
                            # ignored a line, so there is one fewer to report
                            ndiffs -= 1
                            actual_ignored.add(actual_map[i])
                            expected_ignored.add(expected_map[i])
                        else:
                            # difference can't be ignored
                            if first_error_line is None:
                                first_error_line = i + 1
                            if len(failure_cases) < max_permutation_cases:
                                failure_cases.append((i, actual[i],
                                                      expected[i]))

                if first_error_line is not None:
                    first_error = ('%d line%s different, starting at line %d'
                                    % (ndiffs,
                                       's are' if ndiffs != 1 else ' is',
                                       first_error_line))

            # reconstruct variants of the actual and expected to generate
            # two outputs that are different where we found differences, but
            # are the same where we did not find differences (taking into
            # account all of the various 'ignore' and 'remove' parameters)
            if (actual_ignored or expected_ignored
                               or actual_removals
                               or expected_removals):
                reconstruction = self.reconstruct(original_actual,
                                                  original_expected,
                                                  actual_removals,
                                                  expected_removals,
                                                  actual_ignored,
                                                  expected_ignored)
                msgs.add_reconstruction(reconstruction)
        else:
            ndiffs = max_permutation_cases + 1
            first_error = ('%s have different numbers of lines'
                           % ('Files' if actual_path else 'Strings'))

        if ndiffs > 0 and ndiffs <= max_permutation_cases:
            ndiffs = self.check_for_permutation_failures(failure_cases)
        if ndiffs > 0:
            if first_error:
                self.info(msgs, first_error)
            self.add_failures(msgs, reconstruction,
                              actual_path, expected_path,
                              ignore_substrings=ignore_substrings,
                              ignore_patterns=ignore_patterns,
                              preprocess=preprocess, actual=actual,
                              expected=expected)
        return (1 if ndiffs > 0 else 0, msgs)

    def diff_marker(self, left, right):
        prefixend = -1
        for i, (cl, cr) in enumerate(zip(list(left), list(right))):
            prefixend = i
            if cl != cr:
                break
        postfixend = -1
        for i, (cl, cr) in enumerate(zip(reversed(list(left[prefixend+1:])),
                                         reversed(list(right[prefixend+1:])))):
            postfixend = i
            if cl != cr:
                break
        if postfixend > 0:
            middle = '(%s|%s)' % (left[prefixend:-postfixend],
                                  right[prefixend:-postfixend])
            return '*** ' + left[:prefixend] + middle + left[-postfixend:]
        else:
            middle = '(%s|%s)' % (left[prefixend+1:], right[prefixend+1:])
            return '*** ' + left[:prefixend+1] + middle

    def check_patterns(self, cPatterns, actual, expected, i):
        for pattern in cPatterns:
            mExpected = re.match(pattern, expected[i])
            if mExpected:
                mActual = re.match(pattern, actual[i])
                if not mActual:
                    continue
                if pattern.groups < 3:
                    # matched an anchored expression
                    return True
                else:
                    lhs = mActual.group(1) + mActual.group(3)
                    rhs = mExpected.group(1) + mExpected.group(3)
                    if lhs == rhs:
                        actual[i] = mActual.group(1) + '...' + mActual.group(3)
                        expected[i] = (mExpected.group(1)
                                       + '...'
                                       + mExpected.group(3))
                        return True
        return False

    def reconstruct(self, original_actual, original_expected,
                    actual_removals, expected_removals,
                    actual_ignored, expected_ignored):
        rebuilt_actual = []
        rebuilt_expected = []
        iactual = iexpected = 0
        for iout in range(max(len(original_actual),
                              len(original_expected))):
            if (iactual in actual_removals
                    and iexpected in expected_removals):
                # lines which were removed from both sides
                marker = self.diff_marker(original_actual[iactual],
                                          original_expected[iexpected])
                rebuilt_actual.append(marker)
                rebuilt_expected.append(marker)
                iactual += 1
                iexpected += 1
            elif iactual in actual_removals:
                # line removed from just the left
                marker = self.diff_marker(original_actual[iactual], '')
                rebuilt_actual.append(marker)
                rebuilt_expected.append(marker)
                iactual += 1
            elif iexpected in expected_removals:
                # line removed from just the right
                marker = self.diff_marker('', original_expected[iexpected])
                rebuilt_actual.append(marker)
                rebuilt_expected.append(marker)
                iexpected += 1
            elif iactual >= len(original_actual):
                # fallen off the end of the left
                rebuilt_actual.append('LEFT EOF')
                rebuilt_expected.append(original_expected[iexpected])
                iexpected += 1
            elif iexpected >= len(original_expected):
                # fallen off the end of the right
                rebuilt_actual.append(original_actual[iactual])
                rebuilt_expected.append('RIGHT EOF')
            elif (original_actual[iactual] == original_expected[iexpected]):
                # lines are the same, no differences
                rebuilt_actual.append(original_actual[iactual])
                rebuilt_expected.append(original_expected[iexpected])
                iactual += 1
                iexpected += 1
            elif iactual in actual_ignored or iexpected in expected_ignored:
                # lines are different, but differance has been ignored
                marker = self.diff_marker(original_actual[iactual],
                                          original_expected[iexpected])
                rebuilt_actual.append(marker)
                rebuilt_expected.append(marker)
                iactual += 1
                iexpected += 1
            else:
                # difference in line, not ignored, so it's a real difference!
                rebuilt_actual.append(original_actual[iactual])
                rebuilt_expected.append(original_expected[iexpected])
                iactual += 1
                iexpected += 1
        return Reconstruction(rebuilt_actual, rebuilt_expected)

    def check_string_against_file(self, actual, expected_path,
                                  actual_path=None,
                                  lstrip=False, rstrip=False,
                                  ignore_substrings=None,
                                  ignore_patterns=None,
                                  remove_lines=None,
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
            msgs = Diffs()
        try:
            with open(expected_path) as f:
                content = f.read()
                expected_ends_with_newline = content.endswith('\n')
                expected = content.splitlines()
        except IOError:
            self.info(msgs, 'Reference file %s not found.' % expected_path)
            self.add_failures(msgs, None, None, expected_path, actual=actual)
            return (1, msgs)

        if type(actual) in (list, tuple):
            actuals = actual
            actual_ends_with_newline = expected_ends_with_newline
        else:
            actuals = actual.splitlines()
            actual_ends_with_newline = actual.endswith('\n')
        mpc = max_permutation_cases
        (code, msgs) = self.check_strings(actuals, expected,
                                          actual_path=actual_path,
                                          expected_path=expected_path,
                                          lstrip=lstrip, rstrip=rstrip,
                                          ignore_substrings=ignore_substrings,
                                          ignore_patterns=ignore_patterns,
                                          remove_lines=remove_lines,
                                          preprocess=preprocess,
                                          max_permutation_cases=mpc,
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
                   remove_lines=None,
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
            msgs = Diffs()
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
            self.add_failures(msgs, None, actual_path, expected_path)
            return (1, msgs)
        (code, msgs) = self.check_strings(actuals, expected,
                                          actual_path=actual_path,
                                          expected_path=expected_path,
                                          lstrip=lstrip, rstrip=rstrip,
                                          ignore_substrings=ignore_substrings,
                                          ignore_patterns=ignore_patterns,
                                          remove_lines=remove_lines,
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
                    remove_lines=None,
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
            msgs = Diffs()
        for (actual_path, expected_path) in zip(actual_paths, expected_paths):
            try:
                r = self.check_file(actual_path, expected_path,
                                    ignore_substrings=ignore_substrings,
                                    ignore_patterns=ignore_patterns,
                                    remove_lines=remove_lines,
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

    def check_binary_file(self, actual_path, expected_path, msgs=None):
        """
        Check a pair of binary files.
        """
        if msgs is None:
            msgs = Diffs()
        try:
            with open(expected_path, 'rb') as f:
                expected = f.read()
        except IOError:
            self.info(msgs, 'Reference file %s not found.' % expected_path)
            self.info(msgs,
                      'Initialize from actual content with:\n    %s %s %s'
                      % (copycmd(), actual_path, expected_path))
            return (1, msgs)
        try:
            with open(actual_path, 'rb') as f:
                actual = f.read()
        except IOError:
            self.info(msgs, 'Actual file %s not found.'
                            % os.path.normpath(actual_path))
            self.add_failures(msgs, None, actual_path, expected_path)
            return (1, msgs)

        if expected == actual:
            return (0, msgs)
        minlen = min(len(expected), len(actual))
        if expected[:minlen] == actual[:minlen]:
            boff = minlen
        else:
            boff = 0
            while boff < minlen:
                if expected[boff] != actual[boff]:
                    break
                boff += 1
        self.add_failures(msgs, None, actual_path, expected_path,
                          actual=actual, expected=expected,
                          binaryinfo=BinaryInfo(boff,
                                                actualLen=len(actual),
                                                expectedLen=len(expected)))
        return (1, msgs)

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

    def add_failures(self, msgs, reconstruction, actual_path, expected_path,
                     ignore_substrings=None, ignore_patterns=None,
                     preprocess=None, actual=None, expected=None,
                     binaryinfo=None):
        """
        Build a list of messages describing the way in which two files are
        different, and construct an appropriate 'diff' command.
        """
        binary = binaryinfo is not None

        commonname = None
        raw_actual_path = actual_path
        raw_expected_path = expected_path

        if not binary:
            if actual_path and expected_path:
                commonname = os.path.split(actual_path)[1]
            elif actual_path:
                commonname = os.path.split(actual_path)[1]
                tmpExpectedPath = os.path.join(self.tmp_dir,
                                               'expected-raw-' + commonname)
                raw_expected_path = tmpExpectedPath
            elif expected_path:
                commonname = os.path.split(expected_path)[1]
                tmpActualPath = os.path.join(self.tmp_dir,
                                             'actual-raw-' + commonname)
                raw_expected_path = tmpActualPath

        if raw_actual_path and raw_expected_path:
            raw = 'raw' if preprocess or reconstruction else None
            differ = self.compare_with(raw_actual_path, raw_expected_path,
                                       qualifier=raw, binary=binary)
        else:
            differ = None

        if not actual_path or not expected_path:
            if expected_path:
                self.info(msgs, 'Expected file %s' % expected_path)
            elif actual_path:
                self.info(msgs,
                          'Actual file %s' % os.path.normpath(actual_path))
            else:
                self.info(msgs, 'No raw files available for comparison')

        if reconstruction and commonname:
            # show diffs after ignores and removals have been collapsed
            if differ:
                differ = '***\n' + differ + '***\n\n'
            diffActual = os.path.join(self.tmp_dir, 'actual-' + commonname)
            diffExpected = os.path.join(self.tmp_dir, 'expected-' + commonname)
            guide = expected_path or actual_path
            self.write_file(diffActual,
                            (differ or '') + reconstruction.actual_lines(),
                            guide=guide)
            self.write_file(diffExpected,
                             (differ or '') + reconstruction.expected_lines(),
                            guide=guide)
            self.info(msgs, self.compare_with(diffActual, diffExpected,
                                              binary=binary))
        elif differ:
            # show just the 'raw' diffs
            self.info(msgs, differ)

        if ignore_substrings or ignore_patterns:
            self.info(msgs, 'Note exclusions:')
        if ignore_substrings:
            for pattern in ignore_substrings:
                self.info(msgs, '    ' + pattern)
        if ignore_patterns:
            for pattern in ignore_patterns:
                self.info(msgs, '    ' + pattern)
        if binary:
            if binaryinfo.actualLen == binaryinfo.expectedLen:
                lengthinfo = 'both files have length %d' % binaryinfo.actualLen
            else:
                lengthinfo = ('actual length %d, expected length %d'
                              % (binaryinfo.actualLen, binaryinfo.expectedLen))
            self.info(msgs, 'First difference at byte offset %d, %s.'
                      % (binaryinfo.byteoffset, lengthinfo))

    def write_file(self, filename, contents, guide=None):
        """
        Write contents out to a file, optionally taking guidance from an
        existing file as to whether to a newline at the end or not.
        """
        if type(contents) in (list, tuple):
            contents = '\n'.join(contents)
        with open(filename, 'w') as f:
            f.write(contents)
            if guide:
                with open(guide) as fg:
                    lastline = None
                    for line in fg.read():
                        lastline = line
                    if lastline and lastline.endswith('\n'):
                        f.write('\n')

