#
# Unit tests for string functions from tdda.referencetest.checkfiles
#

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import unittest

from tdda.referencetest.checkfiles import FilesComparison


class TestInternals(unittest.TestCase):
    def test_diff_marker(self):
        compare = FilesComparison()
        self.assertEqual(compare.diff_marker("ABC", "XYZ"), "(ABC|XYZ)")
        self.assertEqual(
            compare.diff_marker("ABC:", "ABC: yes"), "ABC:(| yes)"
        )
        self.assertEqual(compare.diff_marker("", "AAA"), "(|AAA)")
        self.assertEqual(compare.diff_marker("AAA", ""), "(AAA|)")
        self.assertEqual(compare.diff_marker("ABC", "AXC"), "A(B|X)C")

    def test_single_pattern(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns(["gr.*t"])
        self.assertTrue(
            compare.check_patterns(cpatterns, "great", "grapefruit")
        )

    def test_unanchored_patterns(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns(["A\d{2}B", "X[a-z]+Y"])
        for actual, expected in [
            ("A22BC", "A99BC"),
            ("XappleY", "XtrafficY"),
            ("A22BXappleY", "A99BXtrafficY"),
            ("froggyA22BXappleY", "froggyA99BXtrafficY"),
            ("frA22BXappleYoggy", "frA99BXtrafficYoggy"),
            ("A22BA99B", "A99BA22B"),
        ]:
            self.assertTrue(
                compare.check_patterns(cpatterns, actual, expected),
                "%s <--> %s" % (actual, expected),
            )
        for actual, expected in [
            ("A222BC", "A99BC"),
            ("222BC", "A99BC"),
            ("XappleYXappleY", "XappleY"),
        ]:
            self.assertFalse(
                compare.check_patterns(cpatterns, actual, expected),
                "%s <--> %s" % (actual, expected),
            )

    def test_anchored_patterns(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns([r"^\d+$"])
        for actual, expected in [
            ("2", "222222222222"),
            ("2", "2"),
            ("02", "2"),
            ("2", "23"),
            ("123", "564"),
        ]:
            self.assertTrue(
                compare.check_patterns(cpatterns, actual, expected),
                "%s <--> %s" % (actual, expected),
            )
        for actual, expected in [
            ("2", "222222222222a22"),
            ("", "23"),
            ("123", ""),
        ]:
            self.assertFalse(
                compare.check_patterns(cpatterns, actual, expected),
                "%s <--> %s" % (actual, expected),
            )

    def test_grouped_pattern(self):
        compare = FilesComparison()
        cpatterns = compare.compile_patterns(["(a|an) (grapefruit|apple)"])
        self.assertTrue(
            compare.check_patterns(cpatterns, "a grapefruit", "an apple")
        )
        self.assertTrue(
            compare.check_patterns(
                cpatterns, "I have a grapefruit", "I have an apple"
            )
        )
        self.assertTrue(
            compare.check_patterns(
                cpatterns,
                "I have a grapefruit and an apple",
                "I have an apple and a grapefruit",
            )
        )
        self.assertFalse(
            compare.check_patterns(
                cpatterns,
                "I have a grapefruit and a banana",
                "I have an apple and a grapefruit",
            )
        )


class TestStrings(unittest.TestCase):
    def test_strings_ok(self):
        compare = FilesComparison()
        self.assertEqual(compare.check_strings([], []), (0, []))
        self.assertEqual(compare.check_strings(["abc"], ["abc"]), (0, []))
        self.assertEqual(
            compare.check_strings(["ab", "c"], ["ab", "c"]), (0, [])
        )

    def test_strings_fail(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings([], ["x"], create_temporaries=False),
            (
                1,
                [
                    "Strings have different numbers of lines, "
                    "differences start at end of actual string",
                    "No files available for comparison",
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(["y"], ["x"], create_temporaries=False),
            (
                1,
                [
                    "1 line is different, starting at line 1",
                    "No files available for comparison",
                ],
            ),
        )

    def test_print(self):
        msgs = []
        compare = FilesComparison(print_fn=lambda x: msgs.append(x))
        compare.check_strings(["a"], ["b"], create_temporaries=False)
        self.assertEqual(
            msgs,
            [
                "1 line is different, starting at line 1",
                "No files available for comparison",
            ],
        )

    def test_strip(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings(
                ["   abc"], ["abc"], create_temporaries=False
            ),
            (
                1,
                [
                    "1 line is different, starting at line 1",
                    "No files available for comparison",
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(["   abc"], ["abc"], lstrip=True), (0, [])
        )
        self.assertEqual(
            compare.check_strings(["abc   "], ["abc"], rstrip=True), (0, [])
        )
        self.assertEqual(
            compare.check_strings(
                ["   abc   "], ["abc"], lstrip=True, rstrip=True
            ),
            (0, []),
        )

    def test_ignore_substrings(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings(
                ["abc", "red", "banana"],
                ["abc", "blue", "grapefruit"],
                create_temporaries=False,
            ),
            (
                1,
                [
                    "2 lines are different, starting at line 2",
                    "No files available for comparison",
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(
                ["abc", "blue", "banana"],
                ["abc", "red", "grapefruit"],
                ignore_substrings=["re"],
                create_temporaries=False,
            ),
            (
                1,
                [
                    "1 line is different, starting at line 3",
                    "No files available for comparison",
                    "Note exclusions:",
                    "    ignore_substrings:",
                    "        re",
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(
                ["abc", "red", "banana"],
                ["abc", "blue", "grapefruit"],
                ignore_substrings=["ue", "gra"],
            ),
            (0, []),
        )

    def test_ignore_patterns(self):
        compare = FilesComparison()

        # red != blue, banana != grapefruit => 2 failures
        self.assertEqual(
            compare.check_strings(
                ["abc", "red", "banana"],
                ["abc", "blue", "grapefruit"],
                create_temporaries=False,
            ),
            (
                1,
                [
                    "2 lines are different, starting at line 2",
                    "No files available for comparison",
                ],
            ),
        )

        # red != blue, banana !~ gr.*t => 2 failures
        self.assertEqual(
            compare.check_strings(
                ["abc", "red", "banana"],
                ["abc", "blue", "grapefruit"],
                ignore_patterns=["gr.*t"],
                create_temporaries=False,
            ),
            (
                1,
                [
                    "2 lines are different, starting at line 2",
                    "No files available for comparison",
                    "Note exclusions:",
                    "    ignore_patterns:",
                    "        gr.*t",
                ],
            ),
        )

        # red != blue, but great DOES ~ gr.*t => 1 failure
        self.assertEqual(
            compare.check_strings(
                ["abc", "red", "great"],
                ["abc", "blue", "grapefruit"],
                ignore_patterns=["gr.*t"],
                create_temporaries=False,
            ),
            (
                1,
                [
                    "1 line is different, starting at line 2",
                    "No files available for comparison",
                    "Note exclusions:",
                    "    ignore_patterns:",
                    "        gr.*t",
                ],
            ),
        )

        # spangle DOES ~ sp......, and breadfruit DOES ~ .*fruit => success
        self.assertEqual(
            compare.check_strings(
                ["abc", "spangle", "breadfruit"],
                ["abc", "spanner", "grapefruit"],
                ignore_patterns=["sp.....", "[bg].*fruit"],
            ),
            (0, []),
        )

    def test_preprocess(self):
        compare = FilesComparison()

        def strip_first_five(strings):
            return [s[5:] for s in strings]

        def strip_first_seven(strings):
            return [s[7:] for s in strings]

        self.assertEqual(
            compare.check_strings(
                ["abc", "spangle", "breadfruit"],
                ["abc", "spanner", "grapefruit"],
                preprocess=strip_first_five,
                create_temporaries=False,
            ),
            (
                1,
                [
                    "1 line is different, starting at line 2",
                    "No files available for comparison",
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(
                ["abc", "spangle", "breadfruit"],
                ["abc", "spanner", "grapefruit"],
                preprocess=strip_first_seven,
            ),
            (0, []),
        )

    def test_permutations(self):
        compare = FilesComparison()
        self.assertEqual(
            compare.check_strings(
                ["abc", "spangle", "spanner"],
                ["spangle", "spanner", "abc"],
                max_permutation_cases=1,
                create_temporaries=False,
            ),
            (
                1,
                [
                    "3 lines are different, starting at line 1",
                    "No files available for comparison",
                ],
            ),
        )
        self.assertEqual(
            compare.check_strings(
                ["abc", "spangle", "spanner"],
                ["abc", "spanner", "spangle"],
                max_permutation_cases=2,
            ),
            (0, []),
        )
        self.assertEqual(
            compare.check_strings(
                ["abc", "spangle", "spanner"],
                ["spangle", "spanner", "abc"],
                max_permutation_cases=3,
            ),
            (0, []),
        )


if __name__ == "__main__":
    unittest.main()
