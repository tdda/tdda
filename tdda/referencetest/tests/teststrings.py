# -*- coding: utf-8 -*-

#
# Unit tests for string functions from tdda.referencetest.checkfiles
#

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import unittest

from tdda.referencetest.checkfiles import FilesComparison


class TestStrings(unittest.TestCase):

    def test_strings_ok(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings([], []), (0, []))
        self.assertEqual(compare.check_strings(['abc'], ['abc']), (0, []))
        self.assertEqual(compare.check_strings(['ab', 'c'], ['ab', 'c']),
                         (0, []))

    def test_strings_fail(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings([], ['x']),
                         (1, ['Strings have different numbers of lines',
                              'No files']))
        self.assertEqual(compare.check_strings(['y'], ['x']),
                         (1, ['1 line is different, starting at line 1',
                              'No files']))

    def test_print(self):
        msgs = []
        compare = FilesComparison(print_fn=lambda x: msgs.append(x))
        compare.check_strings(['a'], ['b'])
        self.assertEqual(msgs, ['1 line is different, starting at line 1',
                                'No files'])

    def test_strip(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings(['   abc'], ['abc']),
                         (1, ['1 line is different, starting at line 1',
                              'No files']))
        self.assertEqual(compare.check_strings(['   abc'], ['abc'],
                                               lstrip=True), (0, []))
        self.assertEqual(compare.check_strings(['abc   '], ['abc'],
                                               rstrip=True), (0, []))
        self.assertEqual(compare.check_strings(['   abc   '], ['abc'],
                                               lstrip=True, rstrip=True),
                         (0, []))

    def test_ignore_substrings(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings(['abc','red', 'banana'],
                                               ['abc','blue', 'grapefruit']),
                         (1, ['2 lines are different, starting at line 2',
                              'No files']))
        self.assertEqual(compare.check_strings(['abc','red', 'banana'],
                                               ['abc','blue', 'grapefruit'],
                                               ignore_substrings=['re']),
                         (1, ['1 line is different, starting at line 3',
                              'No files',
                              'Note exclusions:', '    re']))
        self.assertEqual(compare.check_strings(['abc','red', 'banana'],
                                               ['abc','blue', 'grapefruit'],
                                               ignore_substrings=['ue','gra']),
                         (0, []))

    def test_ignore_patterns(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings(['abc','red', 'banana'],
                                               ['abc','blue', 'grapefruit']),
                         (1, ['2 lines are different, starting at line 2',
                              'No files']))
        self.assertEqual(compare.check_strings(['abc','red', 'banana'],
                                               ['abc','blue', 'grapefruit'],
                                               ignore_patterns=['gr.*t']),
                         (1, ['2 lines are different, starting at line 2',
                              'No files',
                              'Note exclusions:', '    gr.*t']))
        self.assertEqual(compare.check_strings(['abc','spangle', 'breadfruit'],
                                               ['abc','spanner', 'grapefruit'],
                                               ignore_patterns=['sp.....',
                                                                '.*fruit']),
                         (0, []))

    def test_preprocess(self):
        compare = FilesComparison()
        def strip_first_five(strings):
            return [s[5:] for s in strings]
        def strip_first_seven(strings):
            return [s[7:] for s in strings]
        self.assertEqual(compare.check_strings(['abc','spangle', 'breadfruit'],
                                               ['abc','spanner', 'grapefruit'],
                                               preprocess=strip_first_five),
                         (1, ['1 line is different, starting at line 2',
                              'No files']))
        self.assertEqual(compare.check_strings(['abc','spangle', 'breadfruit'],
                                               ['abc','spanner', 'grapefruit'],
                                               preprocess=strip_first_seven),
                         (0, []))

    def test_permutations(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings(['abc','spangle', 'spanner'],
                                               ['spangle','spanner', 'abc'],
                                               max_permutation_cases=1),
                         (1, ['3 lines are different, starting at line 1',
                              'No files']))
        self.assertEqual(compare.check_strings(['abc','spangle', 'spanner'],
                                               ['abc','spanner', 'spangle'],
                                               max_permutation_cases=2),
                         (0, []))
        self.assertEqual(compare.check_strings(['abc','spangle', 'spanner'],
                                               ['spangle','spanner', 'abc'],
                                               max_permutation_cases=3),
                         (0, []))


if __name__ == '__main__':
    unittest.main()
