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


def testdata(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)


class TestFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diffcmd = 'diff' if os.name == 'posix' else 'fc'

    def test_strings_against_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_string_against_file([], testdata('empty.txt'))
        r2 = compare.check_string_against_file('', testdata('empty.txt'))
        r3 = compare.check_string_against_file([''], testdata('empty.txt'))
        r4 = compare.check_string_against_file(['a single line'],
                                               testdata('single.txt'))
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))
        self.assertEqual(r4, (0, []))

    def test_strings_against_files_fail(self):
        compare = FilesComparison()
        r1 = compare.check_string_against_file(['x'], testdata('empty.txt'))
        r2 = compare.check_string_against_file('x', testdata('empty.txt'))
        r3 = compare.check_string_against_file(['', ''], testdata('empty.txt'))
        r4 = compare.check_string_against_file(['the wrong text'],
                                              testdata('single.txt'))
        r5 = compare.check_string_against_file(['the wrong text'],
                                               testdata('single.txt'),
                                               actual_path='wrong.txt')
        self.assertEqual(r1, (1, ['Strings have different numbers of lines',
                                  'Expected file %s' % testdata('empty.txt')]))
        self.assertEqual(r2, (1, ['Strings have different numbers of lines',
                                  'Expected file %s' % testdata('empty.txt')]))
        self.assertEqual(r3, (1, ['Strings have different numbers of lines',
                                  'Expected file %s' % testdata('empty.txt')]))
        self.assertEqual(r4, (1,
                              ['1 line is different, starting at line 1',
                               'Expected file %s' % testdata('single.txt')]))
        diff = '%s %s %s' % (self.diffcmd, 'wrong.txt', testdata('single.txt'))
        self.assertEqual(r5, (1, ['1 line is different, starting at line 1',
                                  'Compare with "%s".' % diff]))

    def test_files_ok(self):
        compare = FilesComparison()
        r1 = compare.check_file(testdata('empty.txt'), testdata('empty.txt'))
        r2 = compare.check_file(testdata('single.txt'), testdata('single.txt'))
        r3 = compare.check_file(testdata('colours.txt'),
                                testdata('colours.txt'))
        self.assertEqual(r1, (0, []))
        self.assertEqual(r2, (0, []))
        self.assertEqual(r3, (0, []))

    def test_files_fail(self):
        compare = FilesComparison()
        r1 = compare.check_file(testdata('empty.txt'), testdata('single.txt'))
        r2 = compare.check_file(testdata('single.txt'), testdata('empty.txt'))
        r3 = compare.check_file(testdata('single.txt'),
                                testdata('colours.txt'))
        diff1 = '%s %s %s' % (self.diffcmd,
                              testdata('empty.txt'), testdata('single.txt'))
        diff2 = '%s %s %s' % (self.diffcmd,
                              testdata('single.txt'), testdata('empty.txt'))
        diff3 = '%s %s %s' % (self.diffcmd,
                              testdata('single.txt'), testdata('colours.txt'))
        self.assertEqual(r1, (1, ['Files have different numbers of lines',
                                  'Compare with "%s".' % diff1]))
        self.assertEqual(r2, (1, ['Files have different numbers of lines',
                                  'Compare with "%s".' % diff2]))
        self.assertEqual(r3, (1, ['Files have different numbers of lines',
                                  'Compare with "%s".' % diff3]))

    def test_multiple_files_ok(self):
        compare = FilesComparison()
        r = compare.check_files([testdata('empty.txt'),
                                 testdata('single.txt'),
                                 testdata('colours.txt')],
                                [testdata('empty.txt'),
                                 testdata('single.txt'),
                                 testdata('colours.txt')])
        self.assertEqual(r, (0, []))

    def test_multiple_files_fail(self):
        compare = FilesComparison()
        r = compare.check_files([testdata('empty.txt'),
                                 testdata('single.txt'),
                                 testdata('colours.txt')],
                                [testdata('single.txt'),
                                 testdata('colours.txt'),
                                 testdata('colours.txt')])
        diff1 = '%s %s %s' % (self.diffcmd,
                              testdata('empty.txt'), testdata('single.txt'))
        diff2 = '%s %s %s' % (self.diffcmd,
                              testdata('single.txt'), testdata('colours.txt'))
        self.assertEqual(r, (2, ['Files have different numbers of lines',
                                 'Compare with "%s".' % diff1,
                                 'Files have different numbers of lines',
                                 'Compare with "%s".' % diff2]))


if __name__ == '__main__':
    unittest.main()
