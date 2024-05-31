# -*- coding: utf-8 -*-

"""
checkfiles.py: comparison mechanism for text files

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2024
"""

import os
import re
import sys
import tempfile
from collections import namedtuple

from tdda.referencetest.basecomparison import (
    BaseComparison, Diffs, copycmd, FailureDiffs
)
from tdda.referencetest.utils import get_encoding, FileType


BinaryInfo = namedtuple(
    'BinaryInfo', ('byteoffset', 'actualLen', 'expectedLen')
)


class FilesComparison(BaseComparison):
    def check_strings(
        self,
        actual,
        expected,
        actual_path=None,
        expected_path=None,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        preprocess=None,
        max_permutation_cases=0,
        create_temporaries=True,
        msgs=None,
        encoding=None,
    ):
        """
        Compare two lists of strings (actual and expected), one-by-one.

        Args:

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
                                should only include explicit anchors if they
                                need refer to the whole line.
                                Only the matched expression within the line
                                is ignored; any text to the left or right
                                of the matched expression must either be
                                the same or be ignorable.
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
            *create_temporaries*
                                controls whether failures cause temporary
                                files to be written.
            *msgs*
                                is an optional Diffs object, where information
                                about differences will be appended; if not
                                specified, a new object will be created and
                                returned.
            *encoding*
                                is a valid Python encoding, or None,
                                for the the reference file.
                                If none, and encoding will be guessed,
                                based on the file extension (currently).

        Returns:

            A FailureDiffs named tuple with:
              .failures     the number of failures
              .diffs        a Diffs object with details of differences
        """

        enc = get_encoding(expected_path, encoding)
        if msgs is None:
            msgs = Diffs()

        normalize = self.normalize_function(lstrip, rstrip)
        permutable = True
        failure_cases = []
        reconstruction = None
        format = None

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
            actual_removals = set(
                [
                    i
                    for i, a in enumerate(original_actual)
                    if any(r in a for r in remove_lines)
                ]
            )
            expected_removals = set(
                [
                    i
                    for i, a in enumerate(original_expected)
                    if any(r in a for r in remove_lines)
                ]
            )
            actual = [
                a
                for i, a in enumerate(original_actual)
                if i not in actual_removals
            ]
            expected = [
                a
                for i, a in enumerate(original_expected)
                if i not in expected_removals
            ]

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

        actual_ignored = set()
        expected_ignored = set()

        if len(actual) == len(expected):
            # Actual and expected now have same number of lines - so we just
            # need to check they are equivalent, line-by-line.
            diffs = [
                i
                for i in range(len(actual))
                if normalize(actual[i]) != normalize(expected[i])
            ]
            if diffs:
                wrong = self.wrong_content(
                    diffs,
                    actual,
                    expected,
                    actual_ignored,
                    expected_ignored,
                    actual_map,
                    expected_map,
                    failure_cases,
                    max_permutation_cases,
                    ignore_substrings=ignore_substrings,
                    ignore_patterns=ignore_patterns,
                )
                (first_error, ndiffs) = wrong
            else:
                first_error = None
                ndiffs = 0
        else:
            # Actual and expected have different numbers of lines, after
            # removal of optional lines.
            wrong = self.wrong_number(
                original_actual,
                original_expected,
                actual_ignored,
                expected_ignored,
                actual_removals,
                expected_removals,
                actual_map,
                expected_map,
                actual_path=actual_path,
                normalize=normalize,
                ignore_substrings=ignore_substrings,
                ignore_patterns=ignore_patterns,
            )
            (first_error, ndiffs) = wrong
            permutable = False

        if (
            preprocess
            or actual_ignored
            or expected_ignored
            or actual_removals
            or expected_removals
            or (actual_path is None and ndiffs > 0)
        ):
            norm_actual = [normalize(s) for s in original_actual]
            norm_expected = [normalize(s) for s in original_expected]
            reconstruction = self.reconstruct(
                norm_actual,
                norm_expected,
                actual_removals,
                expected_removals,
                actual_ignored,
                expected_ignored,
                format=format,
            )
            msgs.add_reconstruction(reconstruction)

        if permutable and ndiffs > 0 and ndiffs <= max_permutation_cases:
            ndiffs = self.check_for_permutation_failures(failure_cases)

        if ndiffs > 0:
            if first_error:
                self.info(msgs, first_error)
            self.add_failures(
                msgs,
                reconstruction,
                actual_path,
                expected_path,
                ignore_substrings=ignore_substrings,
                ignore_patterns=ignore_patterns,
                remove_lines=remove_lines,
                actual=actual,
                expected=expected,
                preprocess=preprocess,
                create_temporaries=create_temporaries,
                encoding=enc,
            )
        return FailureDiffs(failures=1 if ndiffs > 0 else 0, diffs=msgs)

    def wrong_content(
        self,
        diffs,
        actual,
        expected,
        actual_ignored,
        expected_ignored,
        actual_map,
        expected_map,
        failure_cases,
        max_permutation_cases,
        ignore_substrings=None,
        ignore_patterns=None,
    ):
        """
        Deal with the case where the actual and expected have the same
        number of lines (after removing 'removals'), so we need to examine
        those pairs of lines one-by-one to see what 'significant' differences
        there are.
        """
        ndiffs = len(diffs)
        first_error_line = None
        first_error = None
        if ndiffs > 0:
            compiled_patterns = self.compile_patterns(ignore_patterns)
            for i in diffs:
                # 'i' is a line-number in the after-removals datasets
                if self.can_ignore(
                    actual[i],
                    expected[i],
                    ignore_substrings=ignore_substrings,
                    compiled_patterns=compiled_patterns,
                ):
                    # a difference that can be ignored
                    ndiffs -= 1
                    actual_ignored.add(actual_map[i])
                    expected_ignored.add(expected_map[i])
                else:
                    # a difference that cannot be ignored
                    if first_error_line is None:
                        first_error_line = i + 1
                    if len(failure_cases) < max_permutation_cases:
                        failure_cases.append((i, actual[i], expected[i]))

            if first_error_line is not None:
                first_error = '%d line%s different, starting at line %d' % (
                    ndiffs,
                    's are' if ndiffs != 1 else ' is',
                    first_error_line,
                )
        return (first_error, ndiffs)

    def wrong_number(
        self,
        original_actual,
        original_expected,
        actual_ignored,
        expected_ignored,
        actual_removals,
        expected_removals,
        actual_map,
        expected_map,
        actual_path,
        normalize,
        ignore_substrings=None,
        ignore_patterns=None,
    ):
        """
        Deal with the case where the actual and expected have different
        numbers of lines (after removing 'removal' lines).
        """
        compiled_patterns = self.compile_patterns(ignore_patterns)
        desc = 'file' if actual_path else 'string'
        iactual = 0
        iexpected = 0
        first_error_line = None
        ndiffs = 0
        nactual = len(original_actual)
        nexpected = len(original_expected)

        for i in range(min(nactual, nexpected)):
            removed = False
            if iactual in actual_removals:
                iactual += 1
                removed = True
            if iexpected in expected_removals:
                iexpected += 1
                removed = True
            if removed:
                continue
            actual_line = original_actual[iactual]
            expected_line = original_expected[iexpected]
            if normalize(actual_line) == normalize(expected_line):
                iactual += 1
                iexpected += 1
                continue
            if self.can_ignore(
                actual_line,
                expected_line,
                ignore_substrings=ignore_substrings,
                compiled_patterns=compiled_patterns,
            ):
                actual_ignored.add(actual_map[i])
                expected_ignored.add(expected_map[i])
                iactual += 1
                iexpected += 1
                continue
            first_error_line = 'line %d' % (iactual + 1)
            ndiffs += 1

        if first_error_line is None:
            if nactual > nexpected:
                first_error_line = 'end of reference file'
            else:
                first_error_line = 'end of actual %s' % desc

        first_error = (
            '%ss have different numbers of lines, '
            'differences start at %s' % (desc.title(), first_error_line)
        )
        ndiffs = max(len(original_actual), len(original_expected))
        return (first_error, ndiffs)

    def compile_patterns(self, ignore_patterns):
        anchored_patterns = [
            ('' if p.startswith('^') else '^(.*)')
            + ('(%s)' % p)
            + ('' if p.endswith('$') else '(.*)$')
            for p in ignore_patterns or []
        ]
        compiled_patterns = [re.compile(p) for p in anchored_patterns]
        return compiled_patterns

    def can_ignore(
        self,
        actual_line,
        expected_line,
        ignore_substrings=None,
        compiled_patterns=None,
    ):
        """
        Can differences between this actual-line and this expected-line be
        ignored?
        """
        for substr in ignore_substrings or []:
            if substr in expected_line:
                # Note that this only looks in the 'expected' side.
                # This is deliberate, to cover the case where the expected
                # reference file contains concrete representations of things
                # that need to be ignored (like usernames, machine names etc),
                # where you can't express that more generally as any kind of
                # pattern.
                return True
        # not an ignorable substring line, so try patterns
        return self.check_patterns(
            compiled_patterns, actual_line, expected_line
        )

    def check_patterns(self, compiled_patterns, actual_line, expected_line):
        """
        Check a single pair of lines, taking regular-expressions into account.

        It expects the patterns to be in one of the following anchored forms:
            - a one-group pattern like ^(xxx)$
            - a two-group pattern like ^(.*)(xxx)$ or ^(xxx)(.*)$
            - a three-or-more-group pattern like ^(.*)(xxx)(.*)$
              or ^(.*)(xxx)(yyy)(.*)$

        For a one-group pattern, it just needs to fully match both lines.

        For a two-group or three-group pattern, the (xxx) central part of
        the pattern needs to match for both lines, and the remaining (.*)
        parts both need to also match; they don't need to be identical, but
        they need to be 'equivalent' (i.e. by calling check_patterns() on
        these sub-parts, recursively).

        A fixed-string pattern (without any regular-expression components)
        needs to exactly match, on both actual and expected. So this is a
        STRONGER requirement than we have for ignore_substrings, since here
        we are requiring a match for BOTH the actual AND the expected.

        There might be an argument for having a mode where it's just the
        expected that contributes, but that's not currently provided.
        """
        if actual_line == expected_line:
            return True
        for pattern in compiled_patterns or []:
            mExpected = re.match(pattern, expected_line)
            if mExpected:
                mActual = re.match(pattern, actual_line)
                if not mActual:
                    continue
                if pattern.groups in (1, 2):
                    # matched a full-line expression
                    return True
                else:
                    actual_left = mActual.group(1)
                    expected_left = mExpected.group(1)
                    actual_right = mActual.group(pattern.groups)
                    expected_right = mExpected.group(pattern.groups)
                    if self.check_patterns(
                        compiled_patterns, actual_left, expected_left
                    ) and self.check_patterns(
                        compiled_patterns, actual_right, expected_right
                    ):
                        # the .* groups at start and end of both lines
                        #  both match up, so
                        # this pair of lines can be ignored
                        return True
        return False

    def reconstruct(
        self,
        original_actual,
        original_expected,
        actual_removals,
        expected_removals,
        actual_ignored,
        expected_ignored,
        format,
    ):
        """
        Reconstruct variants of the actual and expected to generate
        two outputs that are different where we found differences, but
        are the same where we did not find differences (taking into
        account all of the various 'ignore' and 'remove' parameters)
        """
        rebuilt_actual = []
        rebuilt_expected = []
        iactual = iexpected = 0
        while iactual < len(original_actual) or iexpected < len(
            original_expected
        ):
            if iactual in actual_removals and iexpected in expected_removals:
                # lines which were removed from both sides
                marker = self.diff_marker(
                    original_actual[iactual], original_expected[iexpected]
                )
                rebuilt_actual.append(self.format_marker(marker, format))
                rebuilt_expected.append(self.format_marker(marker, format))
                iactual += 1
                iexpected += 1
            elif iactual in actual_removals:
                # line removed from just the left
                marker = self.diff_marker(original_actual[iactual], '')
                rebuilt_actual.append(self.format_marker(marker, format))
                rebuilt_expected.append(self.format_marker(marker, format))
                iactual += 1
            elif iexpected in expected_removals:
                # line removed from just the right
                marker = self.diff_marker('', original_expected[iexpected])
                rebuilt_actual.append(self.format_marker(marker, format))
                rebuilt_expected.append(self.format_marker(marker, format))
                iexpected += 1
            elif iactual >= len(original_actual):
                # fallen off the end of the left
                rebuilt_expected.append(original_expected[iexpected])
                iexpected += 1
            elif iexpected >= len(original_expected):
                # fallen off the end of the right
                rebuilt_actual.append(original_actual[iactual])
                iactual += 1
            elif original_actual[iactual] == original_expected[iexpected]:
                # lines are the same, no differences
                rebuilt_actual.append(original_actual[iactual])
                rebuilt_expected.append(original_expected[iexpected])
                iactual += 1
                iexpected += 1
            elif iactual in actual_ignored or iexpected in expected_ignored:
                # lines are different, but differance has been ignored
                marker = self.diff_marker(
                    original_actual[iactual], original_expected[iexpected]
                )
                rebuilt_actual.append(self.format_marker(marker, format))
                rebuilt_expected.append(self.format_marker(marker, format))
                iactual += 1
                iexpected += 1
            else:
                # difference in line, not ignored, so it's a real difference!
                rebuilt_actual.append(original_actual[iactual])
                rebuilt_expected.append(original_expected[iexpected])
                iactual += 1
                iexpected += 1
        return Reconstruction(rebuilt_actual, rebuilt_expected)

    def diff_marker(self, left, right):
        """
        Generate a line to insert into the generated set of 'differences'
        which marks lines as:
                COMMON-PREFIX ( ONLY-IN-LEFT | ONLY-IN-RIGHT ) COMMON-SUFFIX
        """
        if left == right:
            return left  # nothing to do
        for i, (cl, cr) in enumerate(zip(list(left), list(right))):
            prefixend = i
            if cl != cr:
                break
        else:
            prefixend = min(len(left), len(right))
        for i, (cl, cr) in enumerate(
            zip(
                reversed(list(left[prefixend:])),
                reversed(list(right[prefixend:])),
            )
        ):
            postfixend = i
            if cl != cr:
                break
        else:
            postfixend = min(len(left[prefixend:]), len(right[prefixend:]))
        if postfixend > 0:
            middle = '(%s|%s)' % (
                left[prefixend:-postfixend],
                right[prefixend:-postfixend],
            )
            marker = left[:prefixend] + middle + left[-postfixend:]
        else:
            middle = '(%s|%s)' % (left[prefixend:], right[prefixend:])
            marker = left[:prefixend] + middle
        return marker

    def format_marker(self, marker, format):
        """
        Format a 'diff marker' in a way that is appropriate for the kind
        of file it is being inserted into. Currently no special kinds of
        formats are treated specially, but it might be possible (though
        difficult) to do something more sensible for HTML files.
        """
        return '*** ' + marker

    def check_string_against_file(
        self,
        actual,
        expected_path,
        actual_path=None,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        preprocess=None,
        max_permutation_cases=0,
        create_temporaries=True,
        msgs=None,
        encoding=None,
    ):
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
        enc = get_encoding(expected_path, encoding)
        if msgs is None:
            msgs = Diffs()
        try:
            with open(expected_path, encoding=enc) as f:
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
        (code, msgs) = self.check_strings(
            actuals,
            expected,
            actual_path=actual_path,
            expected_path=expected_path,
            lstrip=lstrip,
            rstrip=rstrip,
            ignore_substrings=ignore_substrings,
            ignore_patterns=ignore_patterns,
            remove_lines=remove_lines,
            preprocess=preprocess,
            max_permutation_cases=mpc,
            create_temporaries=create_temporaries,
            msgs=msgs,
            encoding=encoding,
        )
        # if expected_ends_with_newline != actual_ends_with_newline:
        #    code = 1
        #    if actual_ends_with_newline:
        #        self.info(msgs, 'Actual string has unexpected newline at end')
        #    else:
        #        self.info(msgs, 'Actual string is missing newline at end')
        return (code, msgs)

    def check_file(
        self,
        actual_path,
        expected_path,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        preprocess=None,
        max_permutation_cases=0,
        msgs=None,
        encoding=None,
    ):
        """
        Check a pair of text files, line by line, with optional
        ignore patterns (substrings) and optionally left-
        and/or right-stripping the contents of both files.

        This is a wrapper around check_strings(), where both the 'actual'
        and 'expected' strings are read from files rather than being passed
        in explicitly.

        Other parameters are the same as for :py:meth:`check_strings()`.
        """
        enc = get_encoding(expected_path, encoding)
        if msgs is None:
            msgs = Diffs()
        try:
            with open(expected_path, encoding=enc) as f:
                content = f.read()
                expected_ends_with_newline = content.endswith('\n')
                expected = content.splitlines()
        except IOError:
            self.info(msgs, 'Reference file %s not found.' % expected_path)
            self.info(
                msgs,
                'Initialize from actual content with:\n    %s %s %s'
                % (copycmd(), actual_path, expected_path),
            )
            return (1, msgs)
        try:
            with open(actual_path, encoding=enc) as f:
                content = f.read()
                actual_ends_with_newline = content.endswith('\n')
                actuals = content.splitlines()
        except IOError:
            self.info(
                msgs,
                'Actual file %s not found.' % os.path.normpath(actual_path),
            )
            self.add_failures(msgs, None, actual_path, expected_path)
            return (1, msgs)
        (code, msgs) = self.check_strings(
            actuals,
            expected,
            actual_path=actual_path,
            expected_path=expected_path,
            lstrip=lstrip,
            rstrip=rstrip,
            ignore_substrings=ignore_substrings,
            ignore_patterns=ignore_patterns,
            remove_lines=remove_lines,
            preprocess=preprocess,
            max_permutation_cases=max_permutation_cases,
            msgs=msgs,
            encoding=enc,
        )
        # if expected_ends_with_newline != actual_ends_with_newline:
        #    code = 1
        #    if actual_ends_with_newline:
        #        self.info(msgs, 'Actual string has unexpected newline at end')
        #    else:
        #        self.info(msgs, 'Actual string is missing newline at end')
        return (code, msgs)

    def check_files(
        self,
        actual_paths,
        expected_paths,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        preprocess=None,
        max_permutation_cases=0,
        msgs=None,
        encodings=None,
    ):
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
        if not encodings:
            encodings = [None] * len(actual_paths)
        for actual_path, expected_path, enc in zip(
            actual_paths, expected_paths, encodings
        ):
            try:
                r = self.check_file(
                    actual_path,
                    expected_path,
                    ignore_substrings=ignore_substrings,
                    ignore_patterns=ignore_patterns,
                    remove_lines=remove_lines,
                    preprocess=preprocess,
                    lstrip=lstrip,
                    rstrip=rstrip,
                    max_permutation_cases=max_permutation_cases,
                    msgs=msgs,
                    encoding=enc,
                )
                (n, msgs) = r
                failures += n
            except Exception as e:
                self.info(
                    msgs,
                    'Error comparing %s and %s (%s %s)'
                    % (
                        os.path.normpath(actual_path),
                        expected_path,
                        e.__class__.__name__,
                        str(e),
                    ),
                )
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
            self.info(
                msgs,
                'Initialize from actual content with:\n    %s %s %s'
                % (copycmd(), actual_path, expected_path),
            )
            return (1, msgs)
        try:
            with open(actual_path, 'rb') as f:
                actual = f.read()
        except IOError:
            self.info(
                msgs,
                'Actual file %s not found.' % os.path.normpath(actual_path),
            )
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
        self.add_failures(
            msgs,
            None,
            actual_path,
            expected_path,
            actual=actual,
            expected=expected,
            binaryinfo=BinaryInfo(
                boff, actualLen=len(actual), expectedLen=len(expected)
            ),
            create_temporaries=False,
        )
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
            self.print_fn('W(%s)' % len(actuals), file=sys.stderr)
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

    def add_failures(
        self,
        msgs,
        reconstruction,
        actual_path,
        expected_path,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        preprocess=None,
        actual=None,
        expected=None,
        binaryinfo=None,
        create_temporaries=True,
        encoding=None,
    ):
        """
        Build a list of messages describing the way in which two files are
        different, and construct an appropriate 'diff' command.

        Also writes both raw actual and processed actual and expected
        if appropriate.
        """
        binary = binaryinfo is not None
        assert not (binary and reconstruction)
        enc = get_encoding(expected_path, encoding)

        commonname = None
        differ = None
        raw_actual_path = actual_path
        raw_expected_path = expected_path

        if create_temporaries:
            if raw_actual_path and raw_expected_path:
                commonname = os.path.split(actual_path)[1]
            else:
                if raw_actual_path:
                    commonname = os.path.split(actual_path)[1]
                elif raw_expected_path:
                    commonname = os.path.split(expected_path)[1]
                else:
                    commonname = 'file'
                if expected is not None and not raw_expected_path:
                    # no raw expected file, so write it
                    tmpExpectedPath = os.path.join(
                        self.tmp_dir, 'expected-raw-' + commonname
                    )
                    raw_expected_path = tmpExpectedPath
                    self.write_file(raw_expected_path, expected)
                if actual is not None and not raw_actual_path:
                    # no raw actual file, so write it
                    tmpActualPath = os.path.join(
                        self.tmp_dir, 'actual-raw-' + commonname
                    )
                    raw_actual_path = tmpActualPath
                    self.write_file(raw_actual_path, actual)

        if raw_actual_path and raw_expected_path:
            raw = 'raw' if (preprocess or reconstruction) else None
            differ = self.compare_with(
                raw_actual_path,
                raw_expected_path,
                qualifier=raw,
                binary=binary,
            )

        if not actual_path or not expected_path:
            if expected_path:
                self.info(msgs, 'Expected file %s' % expected_path)
            elif actual_path:
                self.info(
                    msgs, 'Actual file %s' % os.path.normpath(actual_path)
                )
            elif not create_temporaries:
                self.info(msgs, 'No files available for comparison')

        if differ:
            self.info(msgs, differ)

        if reconstruction and create_temporaries:
            # show diffs after ignores and removals have been collapsed
            if differ:
                differ = '***\n' + differ + '***\n\n'
            diffActual = os.path.join(self.tmp_dir, 'actual-' + commonname)
            diffExpected = os.path.join(self.tmp_dir, 'expected-' + commonname)
            guide = expected_path or actual_path
            self.write_file(
                diffActual,
                (differ or '') + reconstruction.actual_lines(),
                guide=guide,
            )
            self.write_file(
                diffExpected,
                (differ or '') + reconstruction.expected_lines(),
                guide=guide,
            )
            self.info(
                msgs,
                self.compare_with(
                    diffActual, diffExpected, qualifier='post-processed'
                ),
            )

        if ignore_substrings or ignore_patterns or remove_lines:
            self.info(msgs, 'Note exclusions:')
        if ignore_substrings:
            self.info(msgs, '    ignore_substrings:')
            for substr in ignore_substrings:
                self.info(msgs, '        ' + substr)
        if ignore_patterns:
            self.info(msgs, '    ignore_patterns:')
            for pattern in ignore_patterns:
                self.info(msgs, '        ' + pattern)
        if remove_lines:
            self.info(msgs, '    remove_lines:')
            for substr in remove_lines:
                self.info(msgs, '        ' + substr)
        if binary:
            if binaryinfo.actualLen == binaryinfo.expectedLen:
                lengthinfo = 'both files have length %d' % binaryinfo.actualLen
            else:
                lengthinfo = 'actual length %d, expected length %d' % (
                    binaryinfo.actualLen,
                    binaryinfo.expectedLen,
                )
            self.info(
                msgs,
                'First difference at byte offset %d, %s.'
                % (binaryinfo.byteoffset, lengthinfo),
            )

    def write_file(self, filename, contents, guide=None, encoding=None):
        """
        Write contents out to a file, optionally taking guidance from an
        existing file as to whether to a newline at the end or not.
        """
        enc = get_encoding(filename, encoding)
        if type(contents) in (list, tuple):
            contents = '\n'.join(contents)
        with open(filename, 'w', encoding=enc) as f:
            f.write(contents)
            if guide:
                with open(guide, encoding=enc) as fg:
                    lastline = None
                    for line in fg.read():
                        lastline = line
                    if lastline and lastline.endswith('\n'):
                        f.write('\n')


class Reconstruction(object):
    """
    Class for representing 'reconstructions' of the differences between
    a pair of files, in the form of lists of lines from each, where
    ignored and removed items have been 'collapsed' so that the remaining
    differences are just the ones that the comparison considers to be
    actually 'different'.
    """

    def __init__(self, diff_actual, diff_expected):
        self.diff_actual = diff_actual
        self.diff_expected = diff_expected

    def actual_lines(self):
        return '\n'.join(self.diff_actual)

    def expected_lines(self):
        return '\n'.join(self.diff_expected)
