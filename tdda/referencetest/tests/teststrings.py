#
# Unit tests for string functions from tdda.referencetest.checkfiles
#

import os
import tempfile

from tdda.referencetest import ReferenceTestCase, windows_paths_to_posix, tag
from tdda.referencetest.checkfiles import FilesComparison


def refloc(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)


class TestInternals(ReferenceTestCase):
    def test_diff_marker(self):
        compare = FilesComparison()
        self.assertEqual(compare.diff_marker('ABC', 'XYZ'), '(ABC|XYZ)')
        self.assertEqual(
            compare.diff_marker('ABC:', 'ABC: yes'), 'ABC:(| yes)'
        )
        self.assertEqual(compare.diff_marker('', 'AAA'), '(|AAA)')
        self.assertEqual(compare.diff_marker('AAA', ''), '(AAA|)')
        self.assertEqual(compare.diff_marker('ABC', 'AXC'), 'A(B|X)C')

    def test_single_pattern(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns(['gr.*t'])
        self.assertTrue(
            compare.check_patterns(cpatterns, 'great', 'grapefruit')
        )

    def test_unanchored_patterns(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns([r'A\d{2}B', 'X[a-z]+Y'])
        for actual, expected in [
            ('A22BC', 'A99BC'),
            ('XappleY', 'XtrafficY'),
            ('A22BXappleY', 'A99BXtrafficY'),
            ('froggyA22BXappleY', 'froggyA99BXtrafficY'),
            ('frA22BXappleYoggy', 'frA99BXtrafficYoggy'),
            ('A22BA99B', 'A99BA22B'),
        ]:
            self.assertTrue(
                compare.check_patterns(cpatterns, actual, expected),
                '%s <--> %s' % (actual, expected),
            )
        for actual, expected in [
            ('A222BC', 'A99BC'),
            ('222BC', 'A99BC'),
            ('XappleYXappleY', 'XappleY'),
        ]:
            self.assertFalse(
                compare.check_patterns(cpatterns, actual, expected),
                '%s <--> %s' % (actual, expected),
            )

    def test_anchored_patterns(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns([r'^\d+$'])
        for actual, expected in [
            ('2', '222222222222'),
            ('2', '2'),
            ('02', '2'),
            ('2', '23'),
            ('123', '564'),
        ]:
            self.assertTrue(
                compare.check_patterns(cpatterns, actual, expected),
                '%s <--> %s' % (actual, expected),
            )
        for actual, expected in [
            ('2', '222222222222a22'),
            ('', '23'),
            ('123', ''),
        ]:
            self.assertFalse(
                compare.check_patterns(cpatterns, actual, expected),
                '%s <--> %s' % (actual, expected),
            )

    def test_grouped_pattern(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns(['(a|an) (grapefruit|apple)'])
        self.assertTrue(
            compare.check_patterns(cpatterns, 'a grapefruit', 'an apple')
        )
        self.assertTrue(
            compare.check_patterns(
                cpatterns, 'I have a grapefruit', 'I have an apple'
            )
        )
        self.assertTrue(
            compare.check_patterns(
                cpatterns,
                'I have a grapefruit and an apple',
                'I have an apple and a grapefruit',
            )
        )
        self.assertFalse(
            compare.check_patterns(
                cpatterns,
                'I have a grapefruit and a banana',
                'I have an apple and a grapefruit',
            )
        )


class TestStrings(ReferenceTestCase):
    def test_strings_ok(self):
        compare = FilesComparison()
        self.assertFalse(compare.check_strings([], []))
        self.assertFalse(compare.check_strings(['abc'], ['abc']))
        self.assertFalse(compare.check_strings(['ab', 'c'], ['ab', 'c']))

    def test_strings_fail(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings([], ['x'], create_temporaries=False).pair,
            (
                1,
                [
                    'Strings have different numbers of lines, '
                    'differences start at end of actual string',
                    'No files available for comparison',
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(['y'], ['x'], create_temporaries=False).pair,
            (
                1,
                [
                    '1 line is different, starting at line 1',
                    'No files available for comparison',
                ],
            ),
        )

    def test_print(self):
        msgs = []
        compare = FilesComparison(print_fn=lambda x: msgs.append(x))
        compare.check_strings(['a'], ['b'], create_temporaries=False)
        self.assertEqual(
            msgs,
            [
                '1 line is different, starting at line 1',
                'No files available for comparison',
            ],
        )

    def test_strip(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings(
                ['   abc'], ['abc'], create_temporaries=False
            ).pair,
            (
                1,
                [
                    '1 line is different, starting at line 1',
                    'No files available for comparison',
                ],
            ),
        )
        self.assertFalse(
            compare.check_strings(['   abc'], ['abc'], lstrip=True)
        )
        self.assertFalse(
            compare.check_strings(['abc   '], ['abc'], rstrip=True)
        )
        self.assertFalse(
            compare.check_strings(
                ['   abc   '], ['abc'], lstrip=True, rstrip=True
            )
        )

    def test_ignore_substrings(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings(
                ['abc', 'red', 'banana'],
                ['abc', 'blue', 'grapefruit'],
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '2 lines are different, starting at line 2',
                    'No files available for comparison',
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(
                ['abc', 'blue', 'banana'],
                ['abc', 'red', 'grapefruit'],
                ignore_substrings=['re'],
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '1 line is different, starting at line 3',
                    'No files available for comparison',
                    'Note exclusions:',
                    '    ignore_substrings:',
                    '        re',
                ],
            ),
        )
        self.assertFalse(
            compare.check_strings(
                ['abc', 'red', 'banana'],
                ['abc', 'blue', 'grapefruit'],
                ignore_substrings=['ue', 'gra'],
            )
        )

    def test_ignore_patterns(self):
        compare = FilesComparison()

        # red != blue, banana != grapefruit => 2 failures
        self.assertEqual(
            compare.check_strings(
                ['abc', 'red', 'banana'],
                ['abc', 'blue', 'grapefruit'],
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '2 lines are different, starting at line 2',
                    'No files available for comparison',
                ],
            ),
        )

        # red != blue, banana !~ gr.*t => 2 failures
        self.assertEqual(
            compare.check_strings(
                ['abc', 'red', 'banana'],
                ['abc', 'blue', 'grapefruit'],
                ignore_patterns=['gr.*t'],
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '2 lines are different, starting at line 2',
                    'No files available for comparison',
                    'Note exclusions:',
                    '    ignore_patterns:',
                    '        gr.*t',
                ],
            ),
        )

        # red != blue, but great DOES ~ gr.*t => 1 failure
        self.assertEqual(
            compare.check_strings(
                ['abc', 'red', 'great'],
                ['abc', 'blue', 'grapefruit'],
                ignore_patterns=['gr.*t'],
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '1 line is different, starting at line 2',
                    'No files available for comparison',
                    'Note exclusions:',
                    '    ignore_patterns:',
                    '        gr.*t',
                ],
            ),
        )

        # spangle DOES ~ sp......, and breadfruit DOES ~ .*fruit => success
        self.assertFalse(
            compare.check_strings(
                ['abc', 'spangle', 'breadfruit'],
                ['abc', 'spanner', 'grapefruit'],
                ignore_patterns=['sp.....', '[bg].*fruit'],
            )
        )

    def test_preprocess(self):
        compare = FilesComparison()

        def strip_first_five(strings):
            return [s[5:] for s in strings]

        def strip_first_seven(strings):
            return [s[7:] for s in strings]

        self.assertEqual(
            compare.check_strings(
                ['abc', 'spangle', 'breadfruit'],
                ['abc', 'spanner', 'grapefruit'],
                preprocess=strip_first_five,
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '1 line is different, starting at line 2',
                    'No files available for comparison',
                ],
            ),
        )
        self.assertFalse(
            compare.check_strings(
                ['abc', 'spangle', 'breadfruit'],
                ['abc', 'spanner', 'grapefruit'],
                preprocess=strip_first_seven,
            )
        )

    def test_norm_paths(self):
        compare = FilesComparison()
        windows_lines = [
            r'source: C:\Users\runner\work\tdda\small7x5.parquet',
            r'from D:\any\old\dirpath to C:\other\path',
            'no path here',
        ]
        unix_lines = [
            'source: /Users/runner/work/tdda/small7x5.parquet',
            'from /any/old/dirpath to /other/path',
            'no path here',
        ]
        self.assertFalse(
            compare.check_strings(
                windows_lines,
                unix_lines,
                preprocess=windows_paths_to_posix,
            )
        )
        self.assertTrue(
            compare.check_strings(
                windows_lines, unix_lines, create_temporaries=False
            )
        )

    def test_permutations(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings(
                ['abc', 'spangle', 'spanner'],
                ['spangle', 'spanner', 'abc'],
                max_permutation_cases=1,
                create_temporaries=False,
            ).pair,
            (
                1,
                [
                    '3 lines are different, starting at line 1',
                    'No files available for comparison',
                ],
            ),
        )
        self.assertFalse(
            compare.check_strings(
                ['abc', 'spangle', 'spanner'],
                ['abc', 'spanner', 'spangle'],
                max_permutation_cases=2,
            )
        )
        self.assertFalse(
            compare.check_strings(
                ['abc', 'spangle', 'spanner'],
                ['spangle', 'spanner', 'abc'],
                max_permutation_cases=3,
            )
        )

    def test_remove_lines_raw_file_is_unfiltered(self):
        # When check_strings fails and writes a raw actual temp file,
        # lines removed by remove_lines must still appear in that file.
        with tempfile.TemporaryDirectory() as tmp_dir:
            compare = FilesComparison(tmp_dir=tmp_dir)
            actual = [
                'This is a file containing some optional lines.',
                "Here's one: I am optional",
                'And:',
                "Here's another one: I am optional and I have some trailing stuff",
                "And here's a line on its own:",
                'I am optional',
                "That's different",
            ]
            expected = actual[:-1] + ["That's all"]
            compare.check_strings(
                actual,
                expected,
                expected_path=refloc('removals.txt'),
                remove_lines=['I am optional'],
            )
            raw_path = os.path.join(tmp_dir, 'actual-raw-removals.txt')
            with open(raw_path) as f:
                raw_contents = f.read()
        self.assertIn('I am optional', raw_contents)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
