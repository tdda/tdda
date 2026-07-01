# -*- coding: utf-8 -*-

"""
Tests for tdda.rexpy.quality
"""

import os
import unittest

import polars as pl

from tdda.referencetest import ReferenceTestCase, tag

from tdda.rexpy.relib import re

from tdda.rexpy.quality import (
    Alphabets,
    ConcreteRexMetric,
    CountRange,
    DIGIT_CHARS,
    Repeat,
    RexMetrics,
    WHITESPACE_CHARS,
    count_strings,
    count_strings_no_alt,
    _alphabet_spec,
    _as_range,
    _atom_size,
    _charclass_members,
    _charclass_ranges,
    _check_subset,
    _escape_for_charclass,
    _escape_size,
    _intersect_alphabet,
    _matching_paren,
    _merge_ranges,
    _parse_pattern,
    _parse_quantifier,
    _resolve_alphabet,
    _split_alternation,
    _split_top_level,
    _validate_pattern,
)

TESTDATADIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'testdata'
)

FULL_POSTCODES_PATH = os.path.join(TESTDATADIR, 'postcodes-full.parquet')


def full_postcode_data_available():
    """Whether the full (~2.5M-row) UK postcode dataset is present
    locally. Not shipped or committed (see .gitignore) -- nobody
    outside this repo's own development has a way to get hold of
    it, so tests that need it are skipped rather than failing.
    """
    return os.path.exists(FULL_POSTCODES_PATH)


class TestAlphabets(ReferenceTestCase):
    def test_ascii_is_a_bracket_expression(self):
        self.assertEqual(Alphabets.ASCII, '[' + chr(0) + '-' + chr(127) + ']')

    def test_ascii_resolves_to_128(self):
        resolved = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(resolved.size, 128)
        self.assertTrue(resolved.pattern.fullmatch('A'))
        self.assertTrue(resolved.pattern.fullmatch(chr(0)))
        self.assertTrue(resolved.pattern.fullmatch(chr(127)))


class TestValidatePattern(ReferenceTestCase):
    def test_rejects_invalid_regex(self):
        # min > max in {m,n} is syntactically well-formed by our own
        # scan but rejected by re.compile itself
        self.assertRaises(ValueError, _validate_pattern, '^a{2,1}$')
        self.assertRaises(ValueError, _validate_pattern, '^a(b$')

    def test_requires_anchors(self):
        self.assertRaises(ValueError, _validate_pattern, 'ab$')
        self.assertRaises(ValueError, _validate_pattern, '^ab')
        _validate_pattern('^ab$')  # ok, no exception

    def test_rejects_alternation_and_groups(self):
        self.assertRaises(ValueError, _validate_pattern, '^(a|b)$')
        self.assertRaises(ValueError, _validate_pattern, '^a|b$')
        self.assertRaises(ValueError, _validate_pattern, '^(ab)$')

    def test_rejects_unknown_escapes(self):
        self.assertRaises(ValueError, _validate_pattern, r'^\p{L}$')
        self.assertRaises(ValueError, _validate_pattern, r'^\b$')
        self.assertRaises(ValueError, _validate_pattern, r'^a\$')

    def test_accepts_known_escapes(self):
        _validate_pattern(r'^\d\D\w\W\s\S$')
        _validate_pattern(r'^a\.b\-c\(d\)$')

    def test_accepts_bracket_expressions(self):
        _validate_pattern('^[a-z]{2,4}$')
        _validate_pattern('^[^a-z]$')
        _validate_pattern('^[]a]$')  # ']' as first char in class

    def test_rejects_unterminated_bracket(self):
        self.assertRaises(ValueError, _validate_pattern, '^[a-z$')


class TestParseQuantifier(ReferenceTestCase):
    def test_no_quantifier(self):
        self.assertEqual(
            _parse_quantifier('ab', 1, 5), (Repeat(1, 1), 1)
        )

    def test_question_mark(self):
        self.assertEqual(_parse_quantifier('a?', 1, 5), (Repeat(0, 1), 2))

    def test_star(self):
        self.assertEqual(_parse_quantifier('a*', 1, 5), (Repeat(0, 5), 2))

    def test_plus(self):
        self.assertEqual(_parse_quantifier('a+', 1, 5), (Repeat(1, 5), 2))

    def test_exact_braces(self):
        self.assertEqual(
            _parse_quantifier('a{3}', 1, 5), (Repeat(3, 3), 4)
        )

    def test_range_braces(self):
        self.assertEqual(
            _parse_quantifier('a{2,4}', 1, 5), (Repeat(2, 4), 6)
        )

    def test_open_range_braces(self):
        self.assertEqual(
            _parse_quantifier('a{2,}', 1, 5), (Repeat(2, 5), 5)
        )
        self.assertEqual(
            _parse_quantifier('a{7,}', 1, 5), (Repeat(7, 7), 5)
        )

    def test_empty_min_braces(self):
        self.assertEqual(
            _parse_quantifier('a{,3}', 1, 5), (Repeat(0, 3), 5)
        )


class TestParsePattern(ReferenceTestCase):
    def test_literals(self):
        self.assertEqual(
            _parse_pattern('^ab$', 5),
            [('literal', 'a', Repeat(1, 1)), ('literal', 'b', Repeat(1, 1))],
        )

    def test_charclass_and_escape(self):
        self.assertEqual(
            _parse_pattern(r'^[a-c]\d$', 5),
            [
                ('charclass', '[a-c]', Repeat(1, 1)),
                ('charclass', r'\d', Repeat(1, 1)),
            ],
        )

    def test_dot(self):
        self.assertEqual(
            _parse_pattern('^.$', 5), [('charclass', '.', Repeat(1, 1))]
        )

    def test_quantified_charclass(self):
        self.assertEqual(
            _parse_pattern('^[a-c]{2,4}$', 5),
            [('charclass', '[a-c]', Repeat(2, 4))],
        )


class TestCharclassMembers(ReferenceTestCase):
    def test_simple_set(self):
        self.assertEqual(
            _charclass_members('[abc]'), (False, frozenset('abc'))
        )

    def test_range(self):
        self.assertEqual(
            _charclass_members('[a-c]'), (False, frozenset('abc'))
        )

    def test_mixed_range_and_literals(self):
        self.assertEqual(
            _charclass_members('[a-c0-9_]'),
            (False, frozenset('abc0123456789_')),
        )

    def test_negated(self):
        self.assertEqual(
            _charclass_members('[^abc]'), (True, frozenset('abc'))
        )

    def test_literal_close_bracket_first(self):
        self.assertEqual(
            _charclass_members('[]a]'), (False, frozenset(']a'))
        )

    def test_trailing_literal_hyphen(self):
        self.assertEqual(
            _charclass_members('[a-c-]'), (False, frozenset('abc-'))
        )

    def test_escaped_members(self):
        self.assertEqual(
            _charclass_members(r'[\]\-]'), (False, frozenset(']-'))
        )


class TestCharclassRanges(ReferenceTestCase):
    def test_simple_set(self):
        self.assertEqual(
            _charclass_ranges('[abc]'),
            (False, [(ord('a'), ord('a')), (ord('b'), ord('b')),
                     (ord('c'), ord('c'))]),
        )

    def test_range(self):
        self.assertEqual(
            _charclass_ranges('[a-c]'), (False, [(ord('a'), ord('c'))])
        )

    def test_negated(self):
        self.assertEqual(
            _charclass_ranges('[^a-c]'), (True, [(ord('a'), ord('c'))])
        )

    def test_ascii_alphabet(self):
        self.assertEqual(
            _charclass_ranges(Alphabets.ASCII), (False, [(0, 127)])
        )


class TestMergeRanges(ReferenceTestCase):
    def test_no_overlap(self):
        self.assertEqual(
            _merge_ranges([(0, 2), (5, 7)]), [(0, 2), (5, 7)]
        )

    def test_adjacent_ranges_merge(self):
        self.assertEqual(_merge_ranges([(0, 2), (3, 5)]), [(0, 5)])

    def test_overlapping_ranges_merge(self):
        self.assertEqual(_merge_ranges([(0, 5), (3, 8)]), [(0, 8)])

    def test_unsorted_input(self):
        self.assertEqual(
            _merge_ranges([(5, 7), (0, 2)]), [(0, 2), (5, 7)]
        )

    def test_duplicate_singleton_ranges_merge(self):
        # e.g. from a literal alphabet string with repeated chars
        self.assertEqual(
            _merge_ranges([(97, 97), (97, 97), (98, 98)]), [(97, 98)]
        )


class TestEscapeForCharclass(ReferenceTestCase):
    def test_plain_chars(self):
        self.assertEqual(_escape_for_charclass('cba'), 'abc')

    def test_dedupes(self):
        self.assertEqual(_escape_for_charclass('aabbcc'), 'abc')

    def test_escapes_specials(self):
        # sorted by codepoint: '-' (45), '\' (92), ']' (93), '^' (94)
        self.assertEqual(_escape_for_charclass(']^-\\'), r'\-\\\]\^')


class TestAlphabetSpec(ReferenceTestCase):
    def test_bracket_expression_used_as_is(self):
        self.assertEqual(_alphabet_spec('[a-c]'), '[a-c]')

    def test_literal_string_converted(self):
        self.assertEqual(_alphabet_spec('cba'), '[abc]')

    def test_literal_string_with_specials_escaped(self):
        self.assertEqual(_alphabet_spec('a-b'), r'[\-ab]')


class TestResolveAlphabet(ReferenceTestCase):
    def test_none_defaults_to_ascii(self):
        resolved = _resolve_alphabet(None)
        self.assertEqual(resolved.size, 128)

    def test_literal_string(self):
        resolved = _resolve_alphabet('abc')
        self.assertEqual(resolved.size, 3)
        self.assertTrue(resolved.pattern.fullmatch('b'))
        self.assertFalse(resolved.pattern.fullmatch('z'))

    def test_bracket_expression_string(self):
        resolved = _resolve_alphabet('[A-Z0-3]')
        # 26 letters + 4 digits (0-3)
        self.assertEqual(resolved.size, 30)
        self.assertTrue(resolved.pattern.fullmatch('K'))
        self.assertTrue(resolved.pattern.fullmatch('2'))
        self.assertFalse(resolved.pattern.fullmatch('7'))

    def test_rejects_negated_alphabet(self):
        self.assertRaises(ValueError, _resolve_alphabet, '[^a-c]')


class TestCheckSubset(ReferenceTestCase):
    # The four ways `chars` (what the pattern references) and
    # `alphabet` (what's allowed) can relate: only a proper subset
    # or exact match should pass; every other relationship (partial
    # overlap, disjoint, or `chars` being a strict superset of
    # `alphabet`) should raise.

    def test_accepts_exact_match(self):
        _check_subset(
            'abc', _resolve_alphabet('abc'), '^[abc]$'
        )  # no exception

    def test_accepts_proper_subset(self):
        _check_subset(
            'abc', _resolve_alphabet('abcdef'), '^[abc]$'
        )  # no exception

    def test_rejects_partial_overlap(self):
        # 'a' is in chars but not alphabet; 'd' is in alphabet but
        # not chars -- neither is a subset of the other
        self.assertRaises(
            ValueError,
            _check_subset,
            'abc',
            _resolve_alphabet('bcd'),
            '^[a-c]$',
        )

    def test_rejects_disjoint(self):
        self.assertRaises(
            ValueError,
            _check_subset,
            'abc',
            _resolve_alphabet('xyz'),
            '^[abc]$',
        )

    def test_rejects_chars_superset_of_alphabet(self):
        # alphabet is a proper subset of chars, but chars has
        # members ('d' onwards) outside alphabet too
        self.assertRaises(
            ValueError,
            _check_subset,
            'abcdefgh',
            _resolve_alphabet('abc'),
            '^[a-h]$',
        )


class TestIntersectAlphabet(ReferenceTestCase):
    def test_full_overlap(self):
        alphabet = _resolve_alphabet('abcdef')
        self.assertEqual(
            _intersect_alphabet('abc', alphabet, '^[abc]$'), frozenset('abc')
        )

    def test_partial_overlap(self):
        alphabet = _resolve_alphabet('bcd')
        self.assertEqual(
            _intersect_alphabet('abc', alphabet, '^[abc]$'), frozenset('bc')
        )

    def test_raises_when_fully_disjoint(self):
        alphabet = _resolve_alphabet('xyz')
        self.assertRaises(
            ValueError, _intersect_alphabet, 'abc', alphabet, '^[abc]$'
        )


class TestEscapeSize(ReferenceTestCase):
    def test_dot(self):
        # ASCII includes '\n', which '.' never matches (no DOTALL)
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('.', alphabet, '^.$'), 127)

    def test_dot_custom_alphabet(self):
        alphabet = _resolve_alphabet('abc')
        self.assertEqual(_escape_size('.', alphabet, '^.$'), 3)

    def test_dot_excludes_newline_from_alphabet(self):
        alphabet = _resolve_alphabet('ab\n')
        self.assertEqual(_escape_size('.', alphabet, '^.$'), 2)

    def test_dot_unaffected_when_alphabet_has_no_newline(self):
        alphabet = _resolve_alphabet('abc')
        self.assertEqual(_escape_size('.', alphabet, '^.$'), 3)

    def test_digit(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('d', alphabet, r'^\d$'), 10)

    def test_non_digit(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('D', alphabet, r'^\D$'), 128 - 10)

    def test_word(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('w', alphabet, r'^\w$'), 63)

    def test_non_word(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('W', alphabet, r'^\W$'), 128 - 63)

    def test_whitespace(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('s', alphabet, r'^\s$'), 6)

    def test_non_whitespace(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_escape_size('S', alphabet, r'^\S$'), 128 - 6)

    def test_raises_if_canonical_members_outside_alphabet(self):
        # alphabet has no digits at all, but \d needs them
        alphabet = _resolve_alphabet('abc')
        self.assertRaises(ValueError, _escape_size, 'd', alphabet, r'^\d$')

    def test_non_digit_small_custom_alphabet(self):
        # digits plus one extra char: \D is just that extra char
        alphabet = _resolve_alphabet(DIGIT_CHARS + ' ')
        self.assertEqual(_escape_size('D', alphabet, r'^\D$'), 1)

    def test_non_whitespace_small_custom_alphabet(self):
        alphabet = _resolve_alphabet(WHITESPACE_CHARS + 'abc')
        self.assertEqual(_escape_size('S', alphabet, r'^\S$'), 3)

    def test_whitespace_partial_overlap_not_rejected(self):
        # alphabet has ' ' (one of the 6 canonical whitespace
        # chars) but not tab/newline/etc -- partial, not rejected
        alphabet = _resolve_alphabet('[0-9A-Z ]')
        self.assertEqual(_escape_size('s', alphabet, r'^\s$'), 1)

    def test_whitespace_rejected_when_fully_disjoint(self):
        # no whitespace characters in this alphabet at all
        alphabet = _resolve_alphabet('[0-9A-Z]')
        self.assertRaises(ValueError, _escape_size, 's', alphabet, r'^\s$')

    def test_word_raises_when_alphabet_missing_uppercase(self):
        # \w needs uppercase letters too, which this alphabet
        # doesn't have -- unlike \s, \w is strict about this
        alphabet = _resolve_alphabet('abcdefghijklmnopqrstuvwxyz0123456789')
        self.assertRaises(ValueError, _escape_size, 'w', alphabet, r'^\w$')


class TestAtomSize(ReferenceTestCase):
    def test_literal(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_atom_size('literal', 'a', alphabet, '^a$'), 1)

    def test_literal_outside_alphabet(self):
        alphabet = _resolve_alphabet('012')
        self.assertRaises(
            ValueError, _atom_size, 'literal', 'a', alphabet, '^a$'
        )

    def test_bracket(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(
            _atom_size('charclass', '[A-Z]', alphabet, '^[A-Z]$'), 26
        )

    def test_negated_bracket(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(
            _atom_size('charclass', '[^A-Z]', alphabet, '^[^A-Z]$'),
            128 - 26,
        )

    def test_dot(self):
        # ASCII includes '\n', which '.' never matches (no DOTALL)
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(_atom_size('charclass', '.', alphabet, '^.$'), 127)

    def test_escape(self):
        alphabet = _resolve_alphabet(Alphabets.ASCII)
        self.assertEqual(
            _atom_size('charclass', r'\d', alphabet, r'^\d$'), 10
        )


class TestCountStringsNoAlt(ReferenceTestCase):
    def test_single_literal(self):
        self.assertEqual(count_strings_no_alt('^ab$'), 1)

    def test_optional_literal(self):
        self.assertEqual(count_strings_no_alt('^a?b$'), 2)

    def test_fixed_charclass(self):
        self.assertEqual(count_strings_no_alt(r'^\d{4}$'), 10000)

    def test_charclass_range(self):
        # 3**2 + 3**3 + 3**4 = 9 + 27 + 81 = 117
        self.assertEqual(count_strings_no_alt('^[a-c]{2,4}$'), 117)

    def test_plus_expansion(self):
        # sum(26**k for k in 1..3) = 26 + 676 + 17576 = 18278
        self.assertEqual(count_strings_no_alt('^[A-Z]+$', max_plus=3), 18278)

    def test_star_expansion(self):
        # sum(26**k for k in 0..3) = 1 + 26 + 676 + 17576 = 18279
        self.assertEqual(count_strings_no_alt('^[A-Z]*$', max_plus=3), 18279)

    def test_open_brace_expansion(self):
        # sum(26**k for k in 2..3) = 676 + 17576 = 18252
        self.assertEqual(
            count_strings_no_alt('^[A-Z]{2,}$', max_plus=3), 18252
        )

    def test_open_brace_min_above_max_plus(self):
        # min already exceeds max_plus, so no expansion beyond it:
        # exactly 26**5
        self.assertEqual(
            count_strings_no_alt('^[A-Z]{5,}$', max_plus=3), 26**5
        )

    def test_empty_min_brace_expansion(self):
        # sum(26**k for k in 0..3) = 1 + 26 + 676 + 17576 = 18279
        self.assertEqual(count_strings_no_alt('^[A-Z]{,3}$'), 18279)

    def test_combined_postcode_like_pattern(self):
        # 'E' + one or two digits + optional letter, space, digit,
        # two letters
        pattern = r'^E\d{1,2}[A-Z]? \d[A-Z]{2}$'
        expected = (10 + 100) * 27 * 10 * 676
        self.assertEqual(count_strings_no_alt(pattern), expected)

    def test_dot_matches_whole_default_alphabet(self):
        # ASCII includes '\n', which '.' never matches (no DOTALL)
        self.assertEqual(count_strings_no_alt('^.$'), 127)

    def test_dot_matches_whole_custom_alphabet(self):
        self.assertEqual(count_strings_no_alt('^.$', alphabet='abc'), 3)

    def test_negated_escape(self):
        self.assertEqual(count_strings_no_alt(r'^\D$'), 128 - 10)

    def test_negated_bracket(self):
        self.assertEqual(count_strings_no_alt('^[^A-Z]$'), 128 - 26)

    def test_whitespace_size(self):
        self.assertEqual(count_strings_no_alt(r'^\s$'), 6)

    def test_custom_alphabet_bracket_still_exact(self):
        self.assertEqual(count_strings_no_alt('^[a-c]$', alphabet='abcdef'), 3)

    def test_rejects_bracket_char_outside_alphabet(self):
        # disjoint: no overlap at all
        self.assertRaises(
            ValueError, count_strings_no_alt, '^[a-c]$', alphabet='xyz'
        )

    def test_rejects_bracket_partial_overlap_with_alphabet(self):
        # partial overlap: 'a' outside alphabet, 'd' unused by class
        self.assertRaises(
            ValueError, count_strings_no_alt, '^[a-c]$', alphabet='bcd'
        )

    def test_rejects_literal_outside_alphabet(self):
        self.assertRaises(
            ValueError, count_strings_no_alt, '^Z$', alphabet='abc'
        )

    def test_rejects_alternation(self):
        self.assertRaises(ValueError, count_strings_no_alt, '^(a|b)$')

    def test_rejects_unanchored(self):
        self.assertRaises(ValueError, count_strings_no_alt, 'ab')


class TestCountStringsPostcodeAlphabet(ReferenceTestCase):
    # A restricted, realistic alphabet (digits, uppercase, space --
    # no lowercase or underscore), exercised end-to-end.

    ALPHABET = DIGIT_CHARS + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ '

    def test_bracket_pattern_fits_alphabet(self):
        # 'E' + 1-2 digits + optional letter, space, digit, 2 letters
        pattern = r'^E\d{1,2}[A-Z]? \d[A-Z]{2}$'
        expected = (10 + 100) * 27 * 10 * 676
        self.assertEqual(
            count_strings_no_alt(pattern, alphabet=self.ALPHABET),
            expected,
        )

    def test_word_escape_rejected_by_alphabet(self):
        # \w needs lowercase and underscore, absent from this
        # alphabet
        self.assertRaises(
            ValueError,
            count_strings_no_alt,
            r'^\w+$',
            alphabet=self.ALPHABET,
        )

    def test_alternation_over_postcode_alphabet(self):
        result = count_strings(
            r'^(E\d{1,2}|EC\d[A-Z])$', alphabet=self.ALPHABET
        )
        # branch1: 10+100=110; branch2: 10*26=260; disjoint
        self.assertEqual(result, CountRange(260, 370))


class TestAsRange(ReferenceTestCase):
    def test_normalizes_int(self):
        self.assertEqual(_as_range(5), CountRange(5, 5))

    def test_leaves_range_unchanged(self):
        self.assertEqual(_as_range(CountRange(2, 7)), CountRange(2, 7))


class TestMatchingParen(ReferenceTestCase):
    def test_simple(self):
        self.assertEqual(_matching_paren('(ab)', 0), 3)

    def test_nested(self):
        self.assertEqual(_matching_paren('((a)(b))', 0), 7)

    def test_ignores_parens_in_bracket_expression(self):
        self.assertEqual(_matching_paren('(a[()]b)', 0), 7)

    def test_ignores_escaped_paren(self):
        self.assertEqual(_matching_paren(r'(a\)b)', 0), 5)

    def test_raises_if_unterminated(self):
        self.assertRaises(ValueError, _matching_paren, '(ab', 0)


class TestSplitTopLevel(ReferenceTestCase):
    def test_no_separator(self):
        self.assertEqual(_split_top_level('abc', '|'), ['abc'])

    def test_simple_split(self):
        self.assertEqual(_split_top_level('a|b|c', '|'), ['a', 'b', 'c'])

    def test_ignores_separator_in_group(self):
        self.assertEqual(
            _split_top_level('(a|b)|c', '|'), ['(a|b)', 'c']
        )

    def test_ignores_separator_in_bracket_expression(self):
        self.assertEqual(
            _split_top_level('[a|b]|c', '|'), ['[a|b]', 'c']
        )


class TestSplitAlternation(ReferenceTestCase):
    def test_no_alternation(self):
        self.assertEqual(_split_alternation('^abc$'), ['^abc$'])

    def test_simple_alternation(self):
        self.assertEqual(
            _split_alternation('^([a-z]{3}|[0-9]{4})$'),
            ['^[a-z]{3}$', '^[0-9]{4}$'],
        )

    def test_nested_alternation(self):
        self.assertEqual(
            _split_alternation('^((foo|bar)|[0-9]+)$'),
            ['^(foo|bar)$', '^[0-9]+$'],
        )


class TestCountStringsAlternation(ReferenceTestCase):
    def test_no_alternation_returns_int(self):
        result = count_strings('^[a-c]$')
        self.assertEqual(result, 3)
        self.assertIsInstance(result, int)

    def test_alternation_returns_count_range(self):
        # 26**3 disjoint from 10**4: lower = max, upper = sum
        result = count_strings('^([a-z]{3}|[0-9]{4})$')
        self.assertIsInstance(result, CountRange)
        self.assertEqual(result, CountRange(17576, 27576))

    def test_nested_alternation(self):
        # (foo|bar): lower=1, upper=2; combined with [0-9]+ (111110
        # with default max_plus=5): lower=max(1,111110)=111110,
        # upper= 2 + 111110=111112
        result = count_strings('^((foo|bar)|[0-9]+)$')
        self.assertEqual(result, CountRange(111110, 111112))

    def test_rejects_unanchored(self):
        self.assertRaises(ValueError, count_strings, 'a|b')

    def test_max_plus_propagates_to_branches(self):
        # branch1: sum(26**k for k in 1..3) = 26+676+17576 = 18278
        # branch2: 10**2 = 100
        result = count_strings('^([a-z]+|[0-9]{2})$', max_plus=3)
        self.assertEqual(result, CountRange(18278, 18378))

    def test_alphabet_propagates_to_branches(self):
        # both branches fit within the given alphabet
        result = count_strings(
            '^([a-c]|[x-z])$', alphabet='abcxyz'
        )
        self.assertEqual(result, CountRange(3, 6))

    def test_alphabet_violation_propagates_from_branch(self):
        # second branch ([x-z]) references chars outside alphabet
        self.assertRaises(
            ValueError, count_strings, '^([a-c]|[x-z])$', alphabet='abc'
        )


class TestConcreteRexMetricSingleCharAlphabet(ReferenceTestCase):
    # alphabet='a', all_positives=['a']: n_positives=1, min_length=
    # max_length=1, universe=1**1=1

    @classmethod
    def setUpClass(cls):
        cls.q = ConcreteRexMetric(['a'], alphabet='a')

    def test_dot(self):
        score = self.q.evaluate('^.$')
        expected = RexMetrics(len=3, fp=0, fn=0, fpr=0.0, fnr=0.0)
        self.assertTrue(score.eq(expected))

    def test_literal_a(self):
        score = self.q.evaluate('^a$')
        expected = RexMetrics(len=3, fp=0, fn=0, fpr=0.0, fnr=0.0)
        self.assertTrue(score.eq(expected))

    def test_literal_b_rejected_by_alphabet(self):
        self.assertRaises(ValueError, self.q.evaluate, '^b$')

    def test_literal_ab_rejected_by_alphabet(self):
        self.assertRaises(ValueError, self.q.evaluate, '^ab$')

    def test_bracket_a(self):
        score = self.q.evaluate('^[a]$')
        expected = RexMetrics(len=5, fp=0, fn=0, fpr=0.0, fnr=0.0)
        self.assertTrue(score.eq(expected))

    def test_a_one_to_three(self):
        # cardinality = 3 ('a','aa','aaa'); fp = 3 - 1 = 2;
        # fp_denominator = universe(1) - n_positives(1) = 0;
        # fp > 0 over a zero denominator -> +inf
        score = self.q.evaluate('^a{1,3}$')
        expected = RexMetrics(
            len=8, fp=2, fn=0, fpr=float('inf'), fnr=0.0
        )
        self.assertTrue(score.eq(expected))

    def test_a_plus(self):
        # cardinality = 5 (default max_plus): 'a'..'aaaaa'
        score = self.q.evaluate('^a+$')
        expected = RexMetrics(
            len=4, fp=4, fn=0, fpr=float('inf'), fnr=0.0
        )
        self.assertTrue(score.eq(expected))


class TestConcreteRexMetricEmptyStringPositive(ReferenceTestCase):
    # alphabet='a', all_positives=['']: n_positives=1, min_length=
    # max_length=0, universe=1**0=1 -- fully degenerate

    def test_empty_pattern(self):
        q = ConcreteRexMetric([''], alphabet='a')
        score = q.evaluate('^$')
        expected = RexMetrics(len=2, fp=0, fn=0, fpr=0.0, fnr=0.0)
        self.assertTrue(score.eq(expected))


class TestConcreteRexMetricEPostcodes(ReferenceTestCase):
    # Real UK postcode data: the 55 'E...1AA' postcodes in
    # testdata/postcode-subset-e.txt, scored against the
    # loose-to-strict regex progression in
    # ~/python/fAST/postcodes.txt. Added one pattern at a time,
    # each with expected values independently derived by hand (not
    # just copied from running the code), shown in comments.

    ALPHABET = DIGIT_CHARS + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ '

    @classmethod
    def setUpClass(cls):
        path = os.path.join(TESTDATADIR, 'postcode-subset-e.txt')
        with open(path) as f:
            cls.positives = [
                line.rstrip('\n') for line in f if line.strip()
            ]
        cls.q = ConcreteRexMetric(cls.positives, alphabet=cls.ALPHABET)

    def test_setup_sanity(self):
        # 55 postcodes, lengths 6 ('E1 1AA') to 8 ('EC50 1AA'),
        # alphabet = 10 digits + 26 uppercase + space = 37 chars
        self.assertEqual(self.q.n_positives, 55)
        self.assertEqual(self.q.min_length, 6)
        self.assertEqual(self.q.max_length, 8)
        # universe = 37**6 + 37**7 + 37**8
        #          = 2_565_726_409 + 94_931_877_133
        #            + 3_512_479_453_921
        self.assertEqual(self.q.universe, 3_609_977_057_463)

    def test_1_anything_non_empty_default_max_plus(self):
        # default max_plus=5: '.+' only sizes lengths 1-5, well
        # short of our data's actual 6-8 length range
        n_true_positives = 55
        cardinality = sum(37**k for k in range(1, 6))  # 71_270_177
        fp = cardinality - n_true_positives  # 71_270_122 (fn=0: '.+' matches)
        # fp_denominator: 3_609_977_057_408
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^.+$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=4,
            fp=71_270_122,
            fn=0,
            fpr=1.9742541536031995e-05,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_1_anything_non_empty_max_plus_8(self):
        # max_plus=8: '.+' sizes lengths 1-8, including the 1-5
        # portion that falls outside the assumed 6-8-length
        # universe
        n_true_positives = 55
        n_len_1_to_5 = sum(37**k for k in range(1, 6))  # 71_270_177
        n_len_6_to_8 = sum(37**k for k in range(6, 9))  # 3_609_977_057_463
        cardinality = n_len_1_to_5 + n_len_6_to_8  # 3_610_048_327_640
        uncapped_fp = cardinality - n_true_positives  # 3_610_048_327_585
        # fp_denominator: 3_609_977_057_408
        fp_denominator = self.q.universe - n_true_positives
        # uncapped_fp > fp_denominator: a false positive is, by
        # definition, one of the actual negatives, so fp can never
        # legitimately exceed fp_denominator -- clamped, since
        # this is proof of overestimation (cardinality counts lengths
        # 1-5, outside the universe), not a bug

        pattern = r'^.+$'
        score = self.q.evaluate(pattern, max_plus=8)
        expected = RexMetrics(
            len=4,
            fp=3_609_977_057_408,
            fn=0,
            fpr=1.0,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_2_right_length(self):
        # '{6,8}' matches exactly our data's length range, so
        # cardinality == universe: every string of the right length
        # is matched, regardless of content
        n_true_positives = 55
        cardinality = sum(37**k for k in range(6, 9))  # 3_609_977_057_463
        fp = cardinality - n_true_positives  # 3_609_977_057_408 (fn=0)
        # fp_denominator: 3_609_977_057_408 (same number as fp)
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^.{6,8}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=8,
            fp=3_609_977_057_408,
            fn=0,
            fpr=1.0,
            fnr=0.0,
        )
        # fpr == 1.0 exactly (fp == fp_denominator): the least
        # discriminating pattern in the progression, matching any
        # string of the right length whatsoever
        self.assertTrue(score.eq(expected))

    def test_3_right_character_set(self):
        # '[A-Z0-9 ]' is the same 37-char alphabet exactly, so
        # this is equivalent to '.{6,9}' -- one length wider than
        # our data's actual 6-8 range (postcodes.txt's general
        # comment allows up to 9; our subset just doesn't reach
        # it)
        n_true_positives = 55
        n_len_9 = 37**9  # 129_961_739_795_077
        cardinality = self.q.universe + n_len_9  # 133_571_716_852_540
        uncapped_fp = cardinality - n_true_positives  # 133_571_716_852_485
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_977_057_408
        # uncapped_fp >> fp_denominator (length 9 is far more
        # numerous than lengths 6-8 combined) -- clamped, same
        # reasoning as test_1_anything_non_empty_max_plus_8

        pattern = r'^[A-Z0-9 ]{6,9}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=16,
            fp=3_609_977_057_408,
            fn=0,
            fpr=1.0,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_4_broad_structure(self):
        # [A-Z0-9]{2,4} (outward code, 36-char alphabet: letters
        # and digits, no space) + literal space + [0-9] (10) +
        # [A-Z]{2} (676)
        n_outward = sum(36**k for k in range(2, 5))  # 1_727_568
        cardinality = n_outward * 10 * 676  # 11_678_359_680
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 11_678_359_625
        # fp_denominator: 3_609_977_057_408 (fp is well below it,
        # no clamp needed here)
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^[A-Z0-9]{2,4} [0-9][A-Z]{2}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=29,
            fp=11_678_359_625,
            fn=0,
            fpr=0.003235023225711351,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_4_specialized_to_1aa(self):
        # rexpy's own extraction for this data is exactly this
        # specialization of #4: outward code kept generic, inward
        # code fixed to our data's literal '1AA'
        n_outward = sum(36**k for k in range(2, 5))  # 1_727_568
        cardinality = n_outward  # 1_727_568 (literal ' 1AA' suffix)
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 1_727_513
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^[A-Z0-9]{2,4} 1AA$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=19,
            fp=1_727_513,
            fn=0,
            fpr=4.785384983139953e-07,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_e_specialization(self):
        # 'E' area: 'E' + optional 2nd letter (EC, EH, EN, EX...)
        # + 1-2 digits + optional trailing letter (like the 'W'
        # in E1W), then the general inward code
        n_second_letter = 27  # empty (1) + any of 26 letters
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        n_outward = n_second_letter * n_digits * n_trailing_letter
        # n_outward: 80_190
        cardinality = n_outward * 10 * 676  # 542_084_400
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 542_084_345
        # fp_denominator: 3_609_977_057_408
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^E[A-Z]?[0-9]{1,2}[A-Z]? [0-9][A-Z]{2}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=39,
            fp=542_084_345,
            fn=0,
            fpr=0.0001501628227491346,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_e_specialization_with_d_escape(self):
        # same as test_e_specialization but with '\d' instead of
        # '[0-9]': identical metrics, shorter pattern (each '[0-9]'
        # -> '\d' saves 3 chars, 2 occurrences -> 6 shorter)
        n_second_letter = 27  # empty (1) + any of 26 letters
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        n_outward = n_second_letter * n_digits * n_trailing_letter
        # n_outward: 80_190
        cardinality = n_outward * 10 * 676  # 542_084_400
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 542_084_345
        # fp_denominator: 3_609_977_057_408
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^E[A-Z]?\d{1,2}[A-Z]? \d[A-Z]{2}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=33,
            fp=542_084_345,
            fn=0,
            fpr=0.0001501628227491346,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_e_specialization_1aa(self):
        n_second_letter = 27  # empty (1) + any of 26 letters
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        cardinality = n_second_letter * n_digits * n_trailing_letter
        # cardinality: 80_190 (literal ' 1AA' suffix, factor 1)
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 80_135
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^E[A-Z]?[0-9]{1,2}[A-Z]? 1AA$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=29,
            fp=80_135,
            fn=0,
            fpr=2.2198202017809426e-08,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_5_core_structure_no_alternation(self):
        # postcodes.txt pattern 5 without its '|GIR|NPT'
        # alternation (none of our data is GIR/NPT, and
        # count_strings doesn't yet support alternation embedded
        # in a larger sequence anyway): '[A-Z]{1,2}' (1-2 letters)
        # + '[0-9]{1,2}' (1-2 digits) + optional trailing letter,
        # then the general inward code
        n_letters = sum(26**k for k in range(1, 3))  # 702 (1-2 letters)
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        n_outward = n_letters * n_digits * n_trailing_letter
        # n_outward: 2_084_940
        cardinality = n_outward * 10 * 676  # 14_094_194_400
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 14_094_194_345
        # fp_denominator: 3_609_977_057_408
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^[A-Z]{1,2}[0-9]{1,2}[A-Z]? [0-9][A-Z]{2}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=42,
            fp=14_094_194_345,
            fn=0,
            fpr=0.0039042337723663467,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_5_core_structure_no_alternation_1aa(self):
        n_letters = sum(26**k for k in range(1, 3))  # 702 (1-2 letters)
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        cardinality = n_letters * n_digits * n_trailing_letter
        # cardinality: 2_084_940 (literal ' 1AA' suffix, factor 1)
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 2_084_885
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^[A-Z]{1,2}[0-9]{1,2}[A-Z]? 1AA$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=32,
            fp=2_084_885,
            fn=0,
            fpr=5.775341413102965e-07,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_e_area_and_subdistrict_letters_restricted(self):
        # Two refinements at once, hand-crafted from the actual
        # data rather than derived from postcodes.txt: restrict
        # the area's second letter to the ones actually seen
        # ('C', 'H', 'N', 'X', e.g. 'EC', 'EH', 'EN', 'EX') and
        # the subdistrict letter (the trailing letter on London
        # outcodes, e.g. the 'W' in 'E1W', the 'A' in 'EC1A') to
        # the ones actually seen ('A', 'M', 'N', 'P', 'R', 'W',
        # 'Y'), instead of any of the 26 letters for either.
        n_second_letter = 4 + 1  # empty + one of C/H/N/X
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_subdistrict_letter = 7 + 1  # empty + one of AMNPRWY
        cardinality = n_second_letter * n_digits * n_subdistrict_letter
        # cardinality: 4_400 (literal ' 1AA' suffix, factor 1)
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 4_345
        fp_denominator = self.q.universe - n_true_positives

        pattern = r'^E[CNHX]?[0-9]{1,2}[AMNPRWY]? 1AA$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=34,
            fp=4_345,
            fn=0,
            fpr=1.2036087573143065e-09,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_e_full_alternation_all_55(self):
        # The fully specific pattern: a top-level alternation over
        # all 55 actual postcodes (each branch a full literal, since
        # count_strings only supports alternation spanning the
        # entire '^(...)$' body -- the ' 1AA' suffix can't be
        # factored out). Every branch is a distinct literal string,
        # so the true cardinality is exactly 55: no false positives,
        # no false negatives.
        #
        # count_strings's branch heuristic (lower=max branches,
        # upper=sum branches) can't see that the 55 literal branches
        # are disjoint, so cardinality itself comes out as
        # CountRange(1, 55), not the scalar 55. That makes
        # fp.lower = 1 - 55 = -54 before clamping -- an impossible
        # negative false-positive count -- which evaluate() now
        # clamps to 0, then collapses fp/fpr to plain scalars since
        # lower == upper (0) after clamping.
        pattern = '^(' + '|'.join(self.positives) + ')$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=473,
            fp=0,
            fn=0,
            fpr=0.0,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))
        self.assertIsInstance(score.fp, int)
        self.assertIsInstance(score.fpr, float)


@unittest.skipUnless(
    full_postcode_data_available(),
    'full UK postcode dataset not available '
    f'({FULL_POSTCODES_PATH!r}) -- dev-only data, not shipped',
)
class TestConcreteRexMetricFullPostcodes(ReferenceTestCase):
    # The complete (~2.5M-row) UK postcode dataset, rather than just
    # the 55-postcode 'E...1AA' subset used above. Skipped, rather
    # than run, when the data isn't present locally -- see
    # full_postcode_data_available(). testtdda.py additionally
    # removes this class from its own namespace when the data's
    # absent (see there), so the aggregate suite doesn't carry a
    # permanently-skipped test around -- but the normal (non
    # underscore-prefixed) name here matters: pytest's default
    # collection only picks up classes matching `Test*`, and this
    # package is also usable via pytest (see the pytest11 entry
    # point in setup.py), so hiding it behind a leading underscore
    # would make it invisible there, not skipped.

    ALPHABET = DIGIT_CHARS + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ '

    @classmethod
    def setUpClass(cls):
        cls.positives = (
            pl.read_parquet(FULL_POSTCODES_PATH)['Postcode'].to_list()
        )
        cls.q = ConcreteRexMetric(cls.positives, alphabet=cls.ALPHABET)

    def test_setup_sanity(self):
        # 2_527_213 postcodes, lengths 6 ('B1 1AA') to 8
        # ('AB10 1AA'), alphabet = 10 digits + 26 uppercase + space
        # = 37 chars
        self.assertEqual(self.q.n_positives, 2_527_213)
        self.assertEqual(self.q.min_length, 6)
        self.assertEqual(self.q.max_length, 8)
        # universe = 37**6 + 37**7 + 37**8 -- same as the E-subset's,
        # since it depends only on alphabet/length range, not on
        # which or how many postcodes are in the data
        self.assertEqual(self.q.universe, 3_609_977_057_463)

    def test_1_anything_non_empty_default_max_plus(self):
        # default max_plus=5: '.+' only sizes lengths 1-5, well
        # short of our data's actual 6-8 length range. cardinality
        # is identical to the E-subset's (depends only on
        # alphabet/max_plus, not on the data); fp/fpr differ because
        # n_true_positives is now 2_527_213, not 55
        n_true_positives = 2_527_213
        cardinality = sum(37**k for k in range(1, 6))  # 71_270_177
        fp = cardinality - n_true_positives  # 68_742_964 (fn=0)
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250

        pattern = r'^.+$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=4,
            fp=68_742_964,
            fn=0,
            fpr=1.9042506650383314e-05,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_1_anything_non_empty_max_plus_8(self):
        # max_plus=8: '.+' sizes lengths 1-8, including the 1-5
        # portion outside the assumed 6-8-length universe
        n_true_positives = 2_527_213
        n_len_1_to_5 = sum(37**k for k in range(1, 6))  # 71_270_177
        n_len_6_to_8 = sum(37**k for k in range(6, 9))  # 3_609_977_057_463
        cardinality = n_len_1_to_5 + n_len_6_to_8  # 3_610_048_327_640
        uncapped_fp = cardinality - n_true_positives  # 3_610_045_800_427
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250 -- uncapped_fp exceeds
        # it, so fp is clamped (same overestimation-not-a-bug
        # reasoning as the E-subset version of this test)

        pattern = r'^.+$'
        score = self.q.evaluate(pattern, max_plus=8)
        expected = RexMetrics(
            len=4,
            fp=3_609_974_530_250,
            fn=0,
            fpr=1.0,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_2_right_length(self):
        # '{6,8}' matches exactly our data's length range (still
        # true for the full dataset), so cardinality == universe
        n_true_positives = 2_527_213
        cardinality = sum(37**k for k in range(6, 9))  # 3_609_977_057_463
        fp = cardinality - n_true_positives  # 3_609_974_530_250 (fn=0)
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250 (same number as fp)

        pattern = r'^.{6,8}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=8,
            fp=3_609_974_530_250,
            fn=0,
            fpr=1.0,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_3_right_character_set(self):
        # '[A-Z0-9 ]' is the same 37-char alphabet exactly, so this
        # is equivalent to '.{6,9}' -- one length wider than the
        # data's actual 6-8 range
        n_true_positives = 2_527_213
        n_len_9 = 37**9  # 129_961_739_795_077
        cardinality = self.q.universe + n_len_9  # 133_571_716_852_540
        uncapped_fp = cardinality - n_true_positives  # 133_571_714_325_327
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250 -- uncapped_fp far
        # exceeds it (length 9 dwarfs lengths 6-8 combined), clamped

        pattern = r'^[A-Z0-9 ]{6,9}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=16,
            fp=3_609_974_530_250,
            fn=0,
            fpr=1.0,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_4_broad_structure(self):
        # [A-Z0-9]{2,4} (outward code, 36-char alphabet: letters and
        # digits, no space) + literal space + [0-9] (10) +
        # [A-Z]{2} (676). fn=0: every real postcode fits this
        # general shape, not just the E-subset's
        n_outward = sum(36**k for k in range(2, 5))  # 1_727_568
        cardinality = n_outward * 10 * 676  # 11_678_359_680
        n_true_positives = 2_527_213
        fp = cardinality - n_true_positives  # 11_675_832_467
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250

        pattern = r'^[A-Z0-9]{2,4} [0-9][A-Z]{2}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=29,
            fp=11_675_832_467,
            fn=0,
            fpr=0.003234325441678786,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_5_core_structure_no_alternation(self):
        # postcodes.txt pattern 5 without its '|GIR|NPT' alternation
        # (count_strings doesn't support alternation embedded in a
        # larger sequence -- see the E-subset version of this test).
        # Unlike the E-subset (all fn=0), the full dataset actually
        # includes GIR/NPT-prefixed postcodes (special/reserved
        # codes, e.g. 'GIR 0AA', 'NPT 0AD'), which this alternation-
        # free pattern can't match: fn=2_418
        n_letters = sum(26**k for k in range(1, 3))  # 702 (1-2 letters)
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        n_outward = n_letters * n_digits * n_trailing_letter
        # n_outward: 2_084_940
        cardinality = n_outward * 10 * 676  # 14_094_194_400
        n_true_positives = 2_527_213
        fn = 2_418
        n_true_matched = n_true_positives - fn  # 2_524_795
        fp = cardinality - n_true_matched  # 14_091_669_605
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250

        pattern = r'^[A-Z]{1,2}[0-9]{1,2}[A-Z]? [0-9][A-Z]{2}$'
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=42,
            fp=14_091_669_605,
            fn=2_418,
            fpr=0.003903537126624579,
            fnr=0.0009567852017222134,
        )
        self.assertTrue(score.eq(expected))

    def test_6_valid_letters_only_no_alternation(self):
        # Same shape as test_5, but each letter position restricted
        # to the letters actually observed there in the real data
        # (checked directly against the full dataset, not assumed):
        # first area letter never J/Q/V/X; second area letter never
        # I/J/Z; subdistrict letter never I/L/O/Q/Z; each of the two
        # unit letters never C/I/K/M/O/V (the well-known "no
        # confusable letters" rule, confirmed empirically here
        # rather than hard-coded from memory). Still no alternation
        # -- just four narrower character classes -- and fn is
        # unchanged from test_5 (still misses the same GIR/NPT
        # special codes)
        first = 'ABCDEFGHIKLMNOPRSTUWYZ'  # no J/Q/V/X
        second = 'ABCDEFGHKLMNOPQRSTUVWXY'  # no I/J/Z
        subdistrict = 'ABCDEFGHJKMNPRSTUVWXY'  # no I/L/O/Q/Z
        unit = 'ABDEFGHJLNPQRSTUWXYZ'  # no C/I/K/M/O/V
        n_first = len(first)  # 22
        n_second = len(second) + 1  # 24 (empty + one of 23)
        n_digits = sum(10**k for k in range(1, 3))  # 110
        n_subdistrict = len(subdistrict) + 1  # 22 (empty + one of 21)
        n_unit = len(unit)  # 20
        n_outward = n_first * n_second * n_digits * n_subdistrict
        # n_outward: 1_277_760
        cardinality = n_outward * 10 * n_unit * n_unit  # 5_111_040_000
        n_true_positives = 2_527_213
        fn = 2_418
        n_true_matched = n_true_positives - fn  # 2_524_795
        fp = cardinality - n_true_matched  # 5_108_515_205
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250

        pattern = (
            r'^[' + first + r'][' + second + r']?[0-9]{1,2}'
            r'[' + subdistrict + r']? [0-9][' + unit + r']{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=117,
            fp=5_108_515_205,
            fn=2_418,
            fpr=0.001415111148899497,
            fnr=0.0009567852017222134,
        )
        self.assertTrue(score.eq(expected))


if __name__ == '__main__':
    ReferenceTestCase.main()
