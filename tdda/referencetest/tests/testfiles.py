# -*- coding: utf-8 -*-

#
# Unit tests for file functions from tdda.referencetest.checkfiles
#

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import os
import unittest

from tdda.referencetest.checkfiles import FilesComparison
from tdda.referencetest.basecomparison import diffcmd
from tdda.referencetest.utils import normabspath


def refloc(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)


def check(compare, values, filename, diff=False, actual_path=None):
    (code, errs) = compare.check_string_against_file(
        values,
        refloc(filename),
        actual_path=actual_path,
        create_temporaries=False,
    )
    if not diff:
        errs = [e for e in errs if not e.startswith('    ' + diffcmd())]
        errs = [e for e in errs if not e.startswith('Compare with:')]
    return (code, errs)


class TestFiles(unittest.TestCase):
    def test_strings_against_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_string_against_file([], refloc('empty.txt'))
        r2 = compare.check_string_against_file('', refloc('empty.txt'))
        r3 = compare.check_string_against_file([''], refloc('empty.txt'))
        r4 = compare.check_string_against_file(
            ['a single line'], refloc('single.txt')
        )
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))
        self.assertEqual(r4, (0, []))

    def test_strings_against_files_fail(self):
        compare = FilesComparison()
        r1 = check(compare, ['x'], 'empty.txt')
        r2 = check(compare, 'x', 'empty.txt')
        r3 = check(compare, ['', ''], 'empty.txt')
        r4 = check(compare, ['the wrong text\n'], 'single.txt')
        r5 = check(
            compare,
            ['the wrong text\n'],
            'single.txt',
            diff=True,
            actual_path='wrong.txt',
        )
        errs = [
            'Strings have different numbers of lines, '
            'differences start at end of reference file',
            'Expected file %s' % refloc('empty.txt'),
        ]
        self.assertEqual(r1, (1, errs))
        self.assertEqual(r2, (1, errs))
        self.assertEqual(r3, (1, errs))
        self.assertEqual(
            r4,
            (
                1,
                [
                    '1 line is different, starting at line 1',
                    'Expected file %s' % refloc('single.txt'),
                ],
            ),
        )
        diff = '%s %s %s' % (diffcmd(), normabspath('wrong.txt'),
                             refloc('single.txt'))
        self.assertEqual(
            r5,
            (
                1,
                [
                    '1 line is different, starting at line 1',
                    'Compare with:\n    %s\n' % diff,
                ],
            ),
        )

    def test_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_file(refloc('empty.txt'), refloc('empty.txt'))
        r2 = compare.check_file(refloc('single.txt'), refloc('single.txt'))
        r3 = compare.check_file(refloc('colours.txt'), refloc('colours.txt'))
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))

    def test_files_fail(self):
        compare = FilesComparison()
        r1 = compare.check_file(refloc('empty.txt'), refloc('single.txt'))
        r2 = compare.check_file(refloc('single.txt'), refloc('empty.txt'))
        r3 = compare.check_file(refloc('single.txt'), refloc('colours.txt'))
        diff1 = '%s %s %s' % (
            diffcmd(),
            refloc('empty.txt'),
            refloc('single.txt'),
        )
        diff2 = '%s %s %s' % (
            diffcmd(),
            refloc('single.txt'),
            refloc('empty.txt'),
        )
        diff3 = '%s %s %s' % (
            diffcmd(),
            refloc('single.txt'),
            refloc('colours.txt'),
        )
        err1 = (
            'Files have different numbers of lines, '
            'differences start at end of actual file'
        )
        err2 = (
            'Files have different numbers of lines, '
            'differences start at end of reference file'
        )
        err3 = (
            'Files have different numbers of lines, '
            'differences start at line 1'
        )
        self.assertEqual(r1, (1, [err1, 'Compare with:\n    %s\n' % diff1]))
        self.assertEqual(r2, (1, [err2, 'Compare with:\n    %s\n' % diff2]))
        self.assertEqual(r3, (1, [err3, 'Compare with:\n    %s\n' % diff3]))

    def test_file_removals(self):
        compare = FilesComparison()
        r = compare.check_file(
            refloc('removals.txt'),
            refloc('ref.txt'),
            remove_lines=['I am optional'],
        )
        self.assertEqual(r, (0, []))

    def test_multiple_files_ok(self):
        compare = FilesComparison()
        r = compare.check_files(
            [refloc('empty.txt'), refloc('single.txt'), refloc('colours.txt')],
            [refloc('empty.txt'), refloc('single.txt'), refloc('colours.txt')],
        )
        self.assertEqual(r, (0, []))

    def test_multiple_files_fail(self):
        compare = FilesComparison()
        r = compare.check_files(
            [refloc('empty.txt'), refloc('single.txt'), refloc('colours.txt')],
            [
                refloc('single.txt'),
                refloc('colours.txt'),
                refloc('colours.txt'),
            ],
        )
        diff1 = '%s %s %s' % (
            diffcmd(),
            refloc('empty.txt'),
            refloc('single.txt'),
        )
        diff2 = '%s %s %s' % (
            diffcmd(),
            refloc('single.txt'),
            refloc('colours.txt'),
        )
        err1 = (
            'Files have different numbers of lines, '
            'differences start at end of actual file'
        )
        err2 = (
            'Files have different numbers of lines, '
            'differences start at line 1'
        )
        self.assertEqual(
            r,
            (
                2,
                [
                    err1,
                    'Compare with:\n    %s\n' % diff1,
                    err2,
                    'Compare with:\n    %s\n' % diff2,
                ],
            ),
        )

    def test_binary_files(self):
        compare = FilesComparison()
        r1 = compare.check_binary_file(
            refloc('single.txt'), refloc('single.txt')
        )
        r2 = compare.check_binary_file(
            refloc('single.txt'), refloc('double.txt')
        )
        r3 = compare.check_binary_file(
            refloc('double.txt'), refloc('single.txt')
        )
        r4 = compare.check_binary_file(
            refloc('single.txt'), refloc('single2.txt')
        )
        # single2.txt is deliberately not readable in text mode in python3
        self.assertEqual(r1, (0, []))
        diff2 = '%s %s %s' % (diffcmd(), refloc('single.txt'), refloc('double.txt'))
        diff3 = '%s %s %s' % (diffcmd(), refloc('double.txt'), refloc('single.txt'))
        diff4 = '%s %s %s' % (diffcmd(), refloc('single.txt'), refloc('single2.txt'))

        if os.name != 'nt':
            # on Windows, the results will depend on hard-to-predict
            # factors such as how the sources were obtained from git,
            # whether it was a binary build or a source one, etc - so
            # for now we'll just check these on Unix.
            self.assertEqual(
                r2,
                (
                    1,
                    [
                        'Compare with:\n    %s\n' % diff2,
                        'First difference at byte offset 14, '
                        'actual length 14, expected length 28.',
                    ],
                ),
            )
            self.assertEqual(
                r3,
                (
                    1,
                    [
                        'Compare with:\n    %s\n' % diff3,
                        'First difference at byte offset 14, '
                        'actual length 28, expected length 14.',
                    ],
                ),
            )
            self.assertEqual(
                r4,
                (
                    1,
                    [
                        'Compare with:\n    %s\n' % diff4,
                        'First difference at byte offset 2, '
                        'both files have length 14.',
                    ],
                ),
            )

    def test_removal_diffs(self):
        compare = FilesComparison()
        (code, msgs) = compare.check_file(
            refloc('removals.txt'),
            refloc('ref.txt'),
            remove_lines=['I am optional'],
        )
        self.assertEqual(code, 0)
        self.assertEqual(msgs.lines, [])
        self.assertEqual(
            msgs.reconstructions[0].diff_actual,
            [
                'This is a file containing some optional lines.',
                "*** Here's one: I am optional"
                "(|; but it's the only one; "
                "the rest have been removed.)",
                'And:',
                "*** (Here's another one: "
                "I am optional and I have some trailing stuff|)",
                "And here's a line on its own:",
                '*** (I am optional|)',
                "That's all",
            ],
        )
        self.assertEqual(
            msgs.reconstructions[0].diff_expected,
            [
                'This is a file containing some optional lines.',
                "*** Here's one: I am optional"
                "(|; but it's the only one; "
                "the rest have been removed.)",
                'And:',
                "*** (Here's another one: "
                "I am optional and I have some trailing stuff|)",
                "And here's a line on its own:",
                '*** (I am optional|)',
                "That's all",
            ],
        )

    def test_removal_diffs_fail(self):
        compare = FilesComparison()
        (code, msgs) = compare.check_file(
            refloc('removals.txt'),
            refloc('ref.txt'),
            remove_lines=['line', 'And'],
        )
        self.assertEqual(code, 1)
        self.assertEqual(len(msgs.lines), 7)
        self.assertEqual(
            msgs.lines[0],
            'Files have different numbers of lines, '
            'differences start at line 2',
        )
        self.assertTrue(msgs.lines[1].startswith('Compare raw with:\n'))
        self.assertTrue(
            msgs.lines[2].startswith('Compare post-processed with:\n')
        )
        self.assertEqual(
            msgs.reconstructions[0].diff_actual,
            [
                '*** This is a file containing some optional lines.',
                # NEXT LINE IS A REAL DIFFERENCE
                "Here's one: I am optional",
                '*** And:',  # THIS IS REMOVED ON BOTH SIDES
                "*** (|And here's a line on its own:)",
                # NEXT LINE IS A REAL DIFFERENCE
                "Here's another one: "
                "I am optional and I have some trailing stuff",
                "*** (And here's a line on its own:|)",
                # NEXT TWO LINES ARE REAL DIFFERENCES
                'I am optional',
                "That's all",
            ],
        )
        self.assertEqual(
            msgs.reconstructions[0].diff_expected,
            [
                '*** This is a file containing some optional lines.',
                # NEXT LINE IS A REAL DIFFERENCE
                "Here's one: I am optional; but it's the only one; "
                "the rest have been removed.",
                '*** And:',  # THIS IS REMOVED ON BOTH SIDES
                "*** (|And here's a line on its own:)",
                # NEXT LINE IS A REAL DIFFERENCE
                "That's all",
                "*** (And here's a line on its own:|)",
            ],
        )

    def test_ignore_substrings_diffs(self):
        compare = FilesComparison()
        (code, msgs) = compare.check_file(
            refloc('left.txt'),
            refloc('ref.txt'),
            ignore_substrings=['Here\'s one', 'And'],
        )
        difflines = [
            'This is a file containing some optional lines.',
            "*** Here's one: "
            '('
            'And it will get ignored even if not optionally'
            '|'
            'I am optional; but it\'s the only one; '
            'the rest have been'
            ')'
            ' removed.',
            '*** And:'
            '('
            ' this line is different, unless you ignore '
            'the first word'
            '|'
            ')',
            "And here's a line on its own:",
            "That's all",
        ]
        self.assertEqual(code, 0)
        self.assertEqual(msgs.lines, [])
        self.assertEqual(msgs.reconstructions[0].diff_actual, difflines)
        self.assertEqual(msgs.reconstructions[0].diff_expected, difflines)

    def test_ignore_pattern_diffs(self):
        compare = FilesComparison()
        (code, msgs) = compare.check_file(
            refloc('left.txt'),
            refloc('ref.txt'),
            ignore_patterns=['^.*opt...al.*$', '^.*[Aa][Nn][Dd].*$'],
        )
        difflines = [
            'This is a file containing some optional lines.',
            "*** Here's one: "
            '('
            'And it will get ignored even if not optionally'
            '|'
            "I am optional; but it's the only one; the rest have been"
            ')'
            ' removed.',
            '*** And:'
            '('
            ' this line is different, unless you ignore the first word'
            '|'
            ')',
            "And here's a line on its own:",
            "That's all",
        ]
        self.assertEqual(code, 0)
        self.assertEqual(msgs.lines, [])
        self.assertEqual(msgs.reconstructions[0].diff_actual, difflines)
        self.assertEqual(msgs.reconstructions[0].diff_expected, difflines)

    def test_ignore_pattern_diffs_fail(self):
        compare = FilesComparison()
        (code, msgs) = compare.check_file(
            refloc('left.txt'),
            refloc('ref.txt'),
            ignore_patterns=['^.*opt...al.*$'],
        )
        difflines = [
            'This is a file containing some optional lines.',
            "*** Here's one: "
            '('
            'And it will get ignored even if not optionally'
            '|'
            "I am optional; but it's the only one; the rest have been"
            ')'
            ' removed.',
            '... placeholder ...',
            "And here's a line on its own:",
            "That's all",
        ]

        self.assertEqual(code, 1)
        self.assertEqual(len(msgs.lines), 6)
        self.assertEqual(
            msgs.lines[0], '1 line is different, starting at line 3'
        )
        self.assertEqual(msgs.lines[1][:8], 'Compare ')
        self.assertEqual(msgs.lines[2][:8], 'Compare ')
        self.assertEqual(msgs.lines[3], 'Note exclusions:')
        self.assertEqual(msgs.lines[4], '    ignore_patterns:')
        self.assertEqual(msgs.lines[5], '        ^.*opt...al.*$')

        difflines[2] = (
            'And: this line is different, ' 'unless you ignore the first word'
        )
        self.assertEqual(msgs.reconstructions[0].diff_actual, difflines)
        difflines[2] = 'And:'
        self.assertEqual(msgs.reconstructions[0].diff_expected, difflines)


if __name__ == '__main__':
    unittest.main()
