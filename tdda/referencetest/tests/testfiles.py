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


def refloc(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)

def check(compare, values, filename, diff=False, actual_path=None):
    (code, errs) = compare.check_string_against_file(values, refloc(filename),
                                                     actual_path=actual_path)
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
        r4 = compare.check_string_against_file(['a single line'],
                                               refloc('single.txt'))
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
        r5 = check(compare, ['the wrong text\n'], 'single.txt', diff=True,
                   actual_path='wrong.txt')
        self.assertEqual(r1, (1, ['Strings have different numbers of lines',
                                  'Expected file %s' % refloc('empty.txt')]))
        self.assertEqual(r2, (1, ['Strings have different numbers of lines',
                                  'Expected file %s' % refloc('empty.txt')]))
        self.assertEqual(r3, (1, ['Strings have different numbers of lines',
                                  'Expected file %s' % refloc('empty.txt')]))
        self.assertEqual(r4, (1,
                              ['1 line is different, starting at line 1',
                               'Expected file %s' % refloc('single.txt')]))
        diff = '%s %s %s' % (diffcmd(), 'wrong.txt', refloc('single.txt'))
        self.assertEqual(r5, (1, ['1 line is different, starting at line 1',
                                  'Compare with:\n    %s\n' % diff]))

    def test_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_file(refloc('empty.txt'), refloc('empty.txt'))
        r2 = compare.check_file(refloc('single.txt'), refloc('single.txt'))
        r3 = compare.check_file(refloc('colours.txt'),
                                refloc('colours.txt'))
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))

    def test_files_fail(self):
        compare = FilesComparison()
        r1 = compare.check_file(refloc('empty.txt'), refloc('single.txt'))
        r2 = compare.check_file(refloc('single.txt'), refloc('empty.txt'))
        r3 = compare.check_file(refloc('single.txt'),
                                refloc('colours.txt'))
        diff1 = '%s %s %s' % (diffcmd(),
                              refloc('empty.txt'), refloc('single.txt'))
        diff2 = '%s %s %s' % (diffcmd(),
                              refloc('single.txt'), refloc('empty.txt'))
        diff3 = '%s %s %s' % (diffcmd(),
                              refloc('single.txt'), refloc('colours.txt'))
        self.assertEqual(r1, (1, ['Files have different numbers of lines',
                                  'Compare with:\n    %s\n' % diff1]))
        self.assertEqual(r2, (1, ['Files have different numbers of lines',
                                  'Compare with:\n    %s\n' % diff2]))
        self.assertEqual(r3, (1, ['Files have different numbers of lines',
                                  'Compare with:\n    %s\n' % diff3]))

    def test_multiple_files_ok(self):
        compare = FilesComparison()
        r = compare.check_files([refloc('empty.txt'),
                                 refloc('single.txt'),
                                 refloc('colours.txt')],
                                [refloc('empty.txt'),
                                 refloc('single.txt'),
                                 refloc('colours.txt')])
        self.assertEqual(r, (0, []))

    def test_multiple_files_fail(self):
        compare = FilesComparison()
        r = compare.check_files([refloc('empty.txt'),
                                 refloc('single.txt'),
                                 refloc('colours.txt')],
                                [refloc('single.txt'),
                                 refloc('colours.txt'),
                                 refloc('colours.txt')])
        diff1 = '%s %s %s' % (diffcmd(),
                              refloc('empty.txt'), refloc('single.txt'))
        diff2 = '%s %s %s' % (diffcmd(),
                              refloc('single.txt'), refloc('colours.txt'))
        self.assertEqual(r, (2, ['Files have different numbers of lines',
                                 'Compare with:\n    %s\n' % diff1,
                                 'Files have different numbers of lines',
                                 'Compare with:\n    %s\n' % diff2]))


if __name__ == '__main__':
    unittest.main()
