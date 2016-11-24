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


class TestFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diffcmd = 'diff' if os.name == 'posix' else 'fc'

    def test_strings_against_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_string_against_file([], 'testdata/empty.txt')
        r2 = compare.check_string_against_file('', 'testdata/empty.txt')
        r3 = compare.check_string_against_file([''], 'testdata/empty.txt')
        r4 = compare.check_string_against_file(['a single line'],
                                              'testdata/single.txt')
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))
        self.assertEqual(r4, (0, []))

    def test_strings_against_files_fail(self):
        compare = FilesComparison()
        r1 = compare.check_string_against_file(['x'], 'testdata/empty.txt')
        r2 = compare.check_string_against_file('x', 'testdata/empty.txt')
        r3 = compare.check_string_against_file(['', ''], 'testdata/empty.txt')
        r4 = compare.check_string_against_file(['the wrong text'],
                                              'testdata/single.txt')
        r5 = compare.check_string_against_file(['the wrong text'],
                                              'testdata/single.txt',
                                               actual_path='wrong.txt')
        self.assertEqual(r1, (1, ['Strings have different numbers of lines',
                                  'Check failed.',
                                  'Expected file testdata/empty.txt']))
        self.assertEqual(r2, (1, ['Strings have different numbers of lines',
                                  'Check failed.',
                                  'Expected file testdata/empty.txt']))
        self.assertEqual(r3, (1, ['Strings have different numbers of lines',
                                  'Check failed.',
                                  'Expected file testdata/empty.txt']))
        self.assertEqual(r4, (1, ['1 line is different, starting at line 1',
                                  'Check failed.',
                                  'Expected file testdata/single.txt']))
        diff = '%s wrong.txt testdata/single.txt' % self.diffcmd
        self.assertEqual(r5, (1, ['1 line is different, starting at line 1',
                                  'File check failed.',
                                  'Compare with "%s".' % diff]))

    def test_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_file('testdata/empty.txt', 'testdata/empty.txt')
        r2 = compare.check_file('testdata/single.txt', 'testdata/single.txt')
        r3 = compare.check_file('testdata/colours.txt', 'testdata/colours.txt')
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))

    def test_files_fail(self):
        compare = FilesComparison()
        r1 = compare.check_file('testdata/empty.txt', 'testdata/single.txt')
        r2 = compare.check_file('testdata/single.txt', 'testdata/empty.txt')
        r3 = compare.check_file('testdata/single.txt', 'testdata/colours.txt')
        diff1 = '%s testdata/empty.txt testdata/single.txt' % self.diffcmd
        diff2 = '%s testdata/single.txt testdata/empty.txt' % self.diffcmd
        diff3 = '%s testdata/single.txt testdata/colours.txt' % self.diffcmd
        self.assertEqual(r1, (1, ['Files have different numbers of lines',
                                  'File check failed.',
                                  'Compare with "%s".' % diff1]))
        self.assertEqual(r2, (1, ['Files have different numbers of lines',
                                  'File check failed.',
                                  'Compare with "%s".' % diff2]))
        self.assertEqual(r3, (1, ['Files have different numbers of lines',
                                  'File check failed.',
                                  'Compare with "%s".' % diff3]))


if __name__ == '__main__':
    unittest.main()
