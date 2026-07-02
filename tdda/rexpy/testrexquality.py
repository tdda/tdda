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
    _alphabet_spec,
    _as_range,
    _atom_size,
    _charclass_members,
    _charclass_ranges,
    _check_subset,
    _count_sequence,
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

    def test_accepts_unquantified_groups(self):
        _validate_pattern('^(a|b)$')  # ok, no exception
        _validate_pattern('^(ab)$')  # ok, no exception

    def test_rejects_top_level_pipe(self):
        # a bare '|' not inside a group is still invalid here --
        # count_strings strips top-level alternation via
        # _split_alternation before ever reaching _validate_pattern
        self.assertRaises(ValueError, _validate_pattern, '^a|b$')

    def test_rejects_quantified_group(self):
        self.assertRaises(ValueError, _validate_pattern, '^(a|b){2,3}$')
        self.assertRaises(ValueError, _validate_pattern, '^(a|b)+$')
        self.assertRaises(ValueError, _validate_pattern, '^(a|b)?$')

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


class TestCountSequence(ReferenceTestCase):
    def test_single_literal(self):
        self.assertEqual(_count_sequence('^ab$'), 1)

    def test_optional_literal(self):
        self.assertEqual(_count_sequence('^a?b$'), 2)

    def test_fixed_charclass(self):
        self.assertEqual(_count_sequence(r'^\d{4}$'), 10000)

    def test_charclass_range(self):
        # 3**2 + 3**3 + 3**4 = 9 + 27 + 81 = 117
        self.assertEqual(_count_sequence('^[a-c]{2,4}$'), 117)

    def test_plus_expansion(self):
        # sum(26**k for k in 1..3) = 26 + 676 + 17576 = 18278
        self.assertEqual(_count_sequence('^[A-Z]+$', max_plus=3), 18278)

    def test_star_expansion(self):
        # sum(26**k for k in 0..3) = 1 + 26 + 676 + 17576 = 18279
        self.assertEqual(_count_sequence('^[A-Z]*$', max_plus=3), 18279)

    def test_open_brace_expansion(self):
        # sum(26**k for k in 2..3) = 676 + 17576 = 18252
        self.assertEqual(
            _count_sequence('^[A-Z]{2,}$', max_plus=3), 18252
        )

    def test_open_brace_min_above_max_plus(self):
        # min already exceeds max_plus, so no expansion beyond it:
        # exactly 26**5
        self.assertEqual(
            _count_sequence('^[A-Z]{5,}$', max_plus=3), 26**5
        )

    def test_empty_min_brace_expansion(self):
        # sum(26**k for k in 0..3) = 1 + 26 + 676 + 17576 = 18279
        self.assertEqual(_count_sequence('^[A-Z]{,3}$'), 18279)

    def test_combined_postcode_like_pattern(self):
        # 'E' + one or two digits + optional letter, space, digit,
        # two letters
        pattern = r'^E\d{1,2}[A-Z]? \d[A-Z]{2}$'
        expected = (10 + 100) * 27 * 10 * 676
        self.assertEqual(_count_sequence(pattern), expected)

    def test_dot_matches_whole_default_alphabet(self):
        # ASCII includes '\n', which '.' never matches (no DOTALL)
        self.assertEqual(_count_sequence('^.$'), 127)

    def test_dot_matches_whole_custom_alphabet(self):
        self.assertEqual(_count_sequence('^.$', alphabet='abc'), 3)

    def test_negated_escape(self):
        self.assertEqual(_count_sequence(r'^\D$'), 128 - 10)

    def test_negated_bracket(self):
        self.assertEqual(_count_sequence('^[^A-Z]$'), 128 - 26)

    def test_whitespace_size(self):
        self.assertEqual(_count_sequence(r'^\s$'), 6)

    def test_custom_alphabet_bracket_still_exact(self):
        self.assertEqual(_count_sequence('^[a-c]$', alphabet='abcdef'), 3)

    def test_rejects_bracket_char_outside_alphabet(self):
        # disjoint: no overlap at all
        self.assertRaises(
            ValueError, _count_sequence, '^[a-c]$', alphabet='xyz'
        )

    def test_rejects_bracket_partial_overlap_with_alphabet(self):
        # partial overlap: 'a' outside alphabet, 'd' unused by class
        self.assertRaises(
            ValueError, _count_sequence, '^[a-c]$', alphabet='bcd'
        )

    def test_rejects_literal_outside_alphabet(self):
        self.assertRaises(
            ValueError, _count_sequence, '^Z$', alphabet='abc'
        )

    def test_accepts_unquantified_group(self):
        # (a|b): 2 disjoint literals, exact 2
        self.assertEqual(_count_sequence('^(a|b)$'), 2)

    def test_embedded_group_in_sequence(self):
        # 1('X') * 2('(a|b)') * 1('Y') = 2
        self.assertEqual(_count_sequence('^X(a|b)Y$'), 2)

    def test_rejects_quantified_group(self):
        self.assertRaises(ValueError, _count_sequence, '^(a|b){2,3}$')

    def test_rejects_top_level_pipe(self):
        self.assertRaises(ValueError, _count_sequence, '^a|b$')

    def test_rejects_unanchored(self):
        self.assertRaises(ValueError, _count_sequence, 'ab')


class TestCountStringsPostcodeAlphabet(ReferenceTestCase):
    # A restricted, realistic alphabet (digits, uppercase, space --
    # no lowercase or underscore), exercised end-to-end.

    ALPHABET = DIGIT_CHARS + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ '

    def test_bracket_pattern_fits_alphabet(self):
        # 'E' + 1-2 digits + optional letter, space, digit, 2 letters
        pattern = r'^E\d{1,2}[A-Z]? \d[A-Z]{2}$'
        expected = (10 + 100) * 27 * 10 * 676
        self.assertEqual(
            _count_sequence(pattern, alphabet=self.ALPHABET),
            expected,
        )

    def test_word_escape_rejected_by_alphabet(self):
        # \w needs lowercase and underscore, absent from this
        # alphabet
        self.assertRaises(
            ValueError,
            _count_sequence,
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


class TestCountStringsDisjointAlternation(ReferenceTestCase):
    # Plan A: exact cardinality for provably-disjoint alternation
    # branches (all-literal branches, or literal branches plus one
    # non-literal branch that none of the literals match).

    def test_all_literal_branches_exact(self):
        # 3 distinct literals, pairwise disjoint by construction
        result = count_strings('^(cat|dog|fish)$')
        self.assertEqual(result, 3)
        self.assertIsInstance(result, int)

    def test_all_literal_branches_with_duplicate(self):
        # 'cat' appears twice -- dedupe to 2, not 3
        result = count_strings('^(cat|cat|dog)$')
        self.assertEqual(result, 2)
        self.assertIsInstance(result, int)

    def test_literals_plus_one_nonliteral_disjoint_exact(self):
        # GIR, NPT (3 chars each) can't match the general branch
        # (1-2 letters + 1-2 digits + optional letter -- always has
        # a digit), so all 3 branches are disjoint:
        # 2 + _count_sequence('[A-Z]{1,2}[0-9]{1,2}[A-Z]?')
        #   = 2 + 2084940 = 2084942
        result = count_strings('^(GIR|NPT|[A-Z]{1,2}[0-9]{1,2}[A-Z]?)$')
        self.assertEqual(result, 2084942)
        self.assertIsInstance(result, int)

    def test_literal_matches_nonliteral_branch_falls_back(self):
        # 'AB' matches [A-Z]{2} -- branches overlap, so this must
        # stay a CountRange, not be claimed exact
        result = count_strings('^(AB|[A-Z]{2})$')
        self.assertIsInstance(result, CountRange)
        self.assertEqual(result, CountRange(676, 677))

    def test_two_nonliteral_branches_unchanged(self):
        # 2+ non-literal branches: unchanged, existing loose bound
        # (lower=max(676,100)=676, upper=676+100=776)
        result = count_strings('^([A-Z]{2}|[0-9]{2})$')
        self.assertIsInstance(result, CountRange)
        self.assertEqual(result, CountRange(676, 776))

    def test_single_literal_single_nonliteral_edge(self):
        # GIR (3 chars) can't match [A-Z]{1,2} (1-2 chars) -- disjoint
        # 1 + _count_sequence('[A-Z]{1,2}') = 1 + (26+676) = 703
        result = count_strings('^(GIR|[A-Z]{1,2})$')
        self.assertEqual(result, 703)
        self.assertIsInstance(result, int)

    def test_embedded_alternation_exact(self):
        # Plan B: group '(B|C)' is two disjoint literals, exact 2;
        # sequence total = 1('A') * 2 * 1('D') = 2
        result = count_strings('^A(B|C)D$')
        self.assertEqual(result, 2)
        self.assertIsInstance(result, int)

    def test_multiple_embedded_groups_exact(self):
        # Two groups, each exact 2 (disjoint literals); literal '-'
        # contributes 1: total = 2 * 1 * 2 = 4
        result = count_strings('^(A|B)-(C|D)$')
        self.assertEqual(result, 4)
        self.assertIsInstance(result, int)

    def test_embedded_group_overlap_propagates_range(self):
        # Group '(AB|[A-Z]{2})' overlaps internally, same numbers as
        # test_literal_matches_nonliteral_branch_falls_back:
        # CountRange(676, 677). Sequence total =
        # CountRange(676, 677) * 1('X') = CountRange(676, 677)
        result = count_strings('^(AB|[A-Z]{2})X$')
        self.assertIsInstance(result, CountRange)
        self.assertEqual(result, CountRange(676, 677))

    def test_two_groups_one_exact_one_range(self):
        # group1 '(A|B)' exact 2; group2 '(AB|[A-Z]{2})'
        # CountRange(676, 677); elementwise product:
        # CountRange(2*676, 2*677) = CountRange(1352, 1354)
        result = count_strings('^(A|B)(AB|[A-Z]{2})$')
        self.assertIsInstance(result, CountRange)
        self.assertEqual(result, CountRange(1352, 1354))

    def test_quantified_group_still_raises(self):
        # A quantifier on a group is still out of scope -- must
        # raise, not be silently mishandled
        self.assertRaises(ValueError, count_strings, '^(A|B){2,3}$')
        self.assertRaises(ValueError, count_strings, '^(A|B)+$')

    def test_nested_group_inside_embedded_group(self):
        # Inner '(C|D)' exact 2; outer group '(B|(C|D))' is a
        # top-level alternation with one literal branch ('B') and
        # one nested-alternation branch ('(C|D)', itself exact 2) --
        # all-literal-branches-style exactness from Plan A: 1 + 2 = 3
        # sequence total = 1('A') * 3 * 1('E') = 3
        result = count_strings('^A(B|(C|D))E$')
        self.assertEqual(result, 3)
        self.assertIsInstance(result, int)

    def test_literal_plus_nested_alternation_nonliteral_branch(self):
        # Depth-first: the non-literal branch '(NPT|[A-Z]{1,2}[0-9]
        # {1,2}[A-Z]?)' is itself resolved exactly by the same logic
        # one level down (NPT doesn't match the general branch), so
        # the outer level should match the flat 3-branch equivalent:
        # 2 + 2084940 = 2084942
        result = count_strings(
            '^(GIR|(NPT|[A-Z]{1,2}[0-9]{1,2}[A-Z]?))$'
        )
        self.assertEqual(result, 2084942)
        self.assertIsInstance(result, int)

    def test_all_literal_branches_nested_exact(self):
        # Outer split: '(cat|dog)' (non-literal-looking, has parens/
        # '|') and 'fish' (literal). Inner resolves exactly to 2
        # (cat, dog); neither matches 'fish', so outer is exact too:
        # 2 + 1 = 3
        result = count_strings('^((cat|dog)|fish)$')
        self.assertEqual(result, 3)
        self.assertIsInstance(result, int)

    def test_nested_disjointness_partial_tightening(self):
        # Inner branch '(AB|[A-Z]{2})' overlaps internally (AB
        # matches [A-Z]{2}), so it stays CountRange(676, 677) --
        # same as test_literal_matches_nonliteral_branch_falls_back.
        # But GIR (3 chars) can't match the inner branch as a whole
        # (only admits 2-char strings), so the outer level's
        # disjointness check succeeds and tightens the bound:
        # CountRange(1 + 676, 1 + 677) = CountRange(677, 678) --
        # tighter than the naive CountRange(676, 678).
        result = count_strings('^(GIR|(AB|[A-Z]{2}))$')
        self.assertIsInstance(result, CountRange)
        self.assertEqual(result, CountRange(677, 678))


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
        # alternation: '[A-Z]{1,2}' (1-2 letters) + '[0-9]{1,2}'
        # (1-2 digits) + optional trailing letter, then the general
        # inward code
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

    def test_5_with_alternation(self):
        # The real postcodes.txt pattern 5, with its '|GIR|NPT'
        # alternation restored: '(GIR|NPT|[A-Z]{1,2}[0-9]{1,2}
        # [A-Z]?)' followed by the inward code ' [0-9][A-Z]{2}'.
        # This is alternation embedded in a larger sequence (the
        # group isn't the entire ^(...)$ body -- the inward-code
        # suffix follows it), handled by Plan B (embedded groups in
        # a sequence, resolved via range-aware multiplication -- see
        # TestCountSequence). GIR/NPT (3 chars each) can't match the
        # general branch (which always contains a digit), so this
        # resolves exactly.
        n_letters = sum(26**k for k in range(1, 3))  # 702 (1-2 letters)
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        general = n_letters * n_digits * n_trailing_letter  # 2_084_940
        n_inward = 10 * 26**2  # 6_760 (digit + 2 letters)
        # general outward codes, plus GIR/NPT, each paired with
        # every inward code: 2_084_940 * 6_760 + 2 * 6_760
        # = 14_094_194_400 + 13_520 = 14_094_207_920
        cardinality = general * n_inward + 2 * n_inward
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 14_094_207_865
        # fp_denominator: 3_609_977_057_408 (same as the
        # no-alternation version -- doesn't depend on the pattern)
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^(GIR|NPT|[A-Z]{1,2}[0-9]{1,2}[A-Z]?) [0-9][A-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=52,
            fp=14_094_207_865,
            fn=0,
            fpr=0.0039042375175425033,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_6_letters_restricted_with_alternation(self):
        # postcodes.txt group 6: restrict letters to those actually
        # used anywhere, GIR/NPT restored.
        # general: [A-PR-UWYZ](23) * [A-HK-Y]?(1+23=24) *
        # [0-9]{1,2}(110) * [A-HJKMNPR-VWXY]?(1+21=22)
        # = 23*24*110*22 = 1_335_840
        general = 23 * 24 * 110 * 22
        n_outward = general + 2  # GIR, NPT: 1_335_842
        # inward: [0-9](10) * [ABD-HJLNP-VW-Z]{2}(21**2=441)
        n_inward = 10 * 21**2  # 4_410
        cardinality = n_outward * n_inward  # 5_891_063_220
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 5_891_063_165
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^([A-PR-UWYZ][A-HK-Y]?[0-9]{1,2}[A-HJKMNPR-VWXY]?'
            r'|GIR|NPT) [0-9][ABD-HJLNP-VW-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=84,
            fp=5_891_063_165,
            fn=0,
            fpr=0.00163188382400132,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_7_explicit_area_codes(self):
        # postcodes.txt group 7: all 124 valid postal area codes
        # listed explicitly (each a literal), plus GIR/NPT, all
        # disjoint from each other (distinct literals) and from the
        # digit-requiring suffix -- resolves exactly via the same
        # all-literal-branches logic as TestCountStringsDisjointAlternation.
        n_areas = 124
        # each area code + 1-2 digits(110) + optional trailing
        # letter (1+21=22): 124 * 110 * 22 = 300_080
        general = n_areas * 110 * 22
        n_outward = general + 2  # GIR, NPT: 300_082
        n_inward = 10 * 21**2  # 4_410 (same as test_6)
        cardinality = n_outward * n_inward  # 1_323_361_620
        n_true_positives = 55
        fp = cardinality - n_true_positives  # 1_323_361_565
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            '^((AB|AL|B|BA|BB|BD|BH|BL|BN|BR|BS|BT|CA|CB|CF|CH|CM|'
            'CO|CR|CT|CV|CW|DA|DD|DE|DG|DH|DL|DN|DT|DY|E|EC|EH|EN|'
            'EX|FK|FY|G|GL|GU|GY|HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|'
            'IV|JE|KA|KT|KW|KY|L|LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|N|'
            'NE|NG|NN|NP|NR|NW|OL|OX|PA|PE|PH|PL|PO|PR|RG|RH|RM|S|'
            'SA|SE|SG|SK|SL|SM|SN|SO|SP|SR|SS|ST|SW|SY|TA|TD|TF|TN|'
            'TQ|TR|TS|TW|UB|W|WA|WC|WD|WF|WN|WR|WS|WV|YO|ZE)'
            '[0-9]{1,2}[A-HJKMNPR-VWXY]?|GIR|NPT) '
            '[0-9][ABD-HJLNP-VW-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=429,
            fp=1_323_361_565,
            fn=0,
            fpr=0.00036658448071971597,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_8_government_transfer_spec(self):
        # postcodes.txt group 8: sourced from the UK government's
        # official "Bulk Data Transfer - additional validation"
        # spec (valid from 12 November 2015):
        # https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/488478/Bulk_Data_Transfer_-_additional_validation_valid_from_12_November_2015.pdf
        #
        # Original (mixed-case) regex from that document:
        # ^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|
        # (([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9]
        # [A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z]))))
        # [0-9][A-Za-z]{2})$
        #
        # postcodes.txt's version below strips the lowercase
        # alternatives (uppercase-only, matching this codebase's
        # convention elsewhere) and wraps the whole alternation in
        # one group so it's valid input to count_strings (the
        # original, as published, has a bare top-level '|' outside
        # any wrapping group -- harmless under re.fullmatch, since
        # fullmatch anchors regardless of internal ^/$ placement, but
        # not valid as a single ^(...)$ body). Confirmed behaviorally
        # identical to the properly-nested version below by
        # fullmatch-testing 200,000 random candidate strings, zero
        # mismatches.
        #
        # 'GIR 0AA' as an explicit literal, plus 4 non-literal
        # structural forms (2+ non-literal branches in the embedded
        # group -- Plan A's exactness doesn't reach this, so it's a
        # genuine CountRange, not a bug). Each form's cardinality
        # (all disjoint from 'GIR 0AA' by construction/length):
        # b1 = [A-Z][0-9]{1,2} = 26*110 = 2_860
        # b2 = [A-Z][A-HJ-Y][0-9]{1,2} = 26*23*110 = 65_780
        # b3 = [A-Z][0-9][A-Z] = 26*10*26 = 6_760
        # b4 = [A-Z][A-HJ-Y][0-9]?[A-Z] = 26*23*11*26 = 171_028
        b1 = 26 * 110
        b2 = 26 * 23 * 110
        b3 = 26 * 10 * 26
        b4 = 26 * 23 * 11 * 26
        # lower=max(branches), upper=sum(branches) -- existing
        # 2+-non-literal-branch bound, unchanged by Plan A/B
        grp_lower = max(b1, b2, b3, b4)  # 171_028
        grp_upper = b1 + b2 + b3 + b4  # 246_428
        n_inward = 10 * 26**2  # 6_760
        # group's contribution, paired with inward, plus 'GIR 0AA'
        # (1 string) at the outer level (disjoint: different length/
        # shape from every form above):
        cardinality_lower = 1 + grp_lower * n_inward  # 1_156_349_681...
        cardinality_upper = 1 + grp_upper * n_inward
        n_true_positives = 55
        fp_lower = cardinality_lower - n_true_positives
        fp_upper = cardinality_upper - n_true_positives
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^(GIR 0AA|([A-Z][0-9]{1,2}|[A-Z][A-HJ-Y][0-9]{1,2}'
            r'|[A-Z][0-9][A-Z]|[A-Z][A-HJ-Y][0-9]?[A-Z]) '
            r'[0-9][A-Z]{2})$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=108,
            fp=CountRange(1_206_416_586, 1_735_454_186),
            fn=0,
            fpr=CountRange(
                0.00033418954381561063, 0.00048073828680952164
            ),
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_9_full_royal_mail_spec(self):
        # postcodes.txt group 9: the full Royal Mail spec as a
        # single combined regex, restricted letter classes (same
        # spirit as test_8, tighter classes). 4 non-literal forms,
        # each requiring exactly one digit -- unlike test_8's form
        # b4, there's no optional-digit form here, so (unlike
        # pattern 8) this genuinely does NOT match NPT (see
        # test_9_full_royal_mail_spec in
        # TestConcreteRexMetricFullPostcodes for the real-data
        # confirmation; the E-subset has no NPT postcodes, so fn=0
        # here regardless).
        # c1 = [A-PR-UWYZ][0-9][0-9A-HJKPSTUW]? = 23*10*(1+25)=5_980
        # c2 = [A-PR-UWYZ][A-HK-Y][0-9][0-9ABEHMNPRVWXY]?
        #    = 23*23*10*(1+22) = 121_670
        # c3 = [A-PR-UWYZ][0-9][A-HJKSTUW] = 23*10*14 = 3_220
        # c4 = [A-PR-UWYZ][A-HK-Y][0-9][ABEHMNPRVWXY] = 23*23*10*12
        #    = 63_480
        c1 = 23 * 10 * (1 + 25)
        c2 = 23 * 23 * 10 * (1 + 22)
        c3 = 23 * 10 * 14
        c4 = 23 * 23 * 10 * 12
        grp_lower = max(c1, c2, c3, c4)  # 121_670
        grp_upper = c1 + c2 + c3 + c4  # 194_350
        n_inward = 10 * 21**2  # 4_410
        cardinality_lower = grp_lower * n_inward + 1  # 'GIR 0AA'
        cardinality_upper = grp_upper * n_inward + 1
        n_true_positives = 55
        fp_lower = cardinality_lower - n_true_positives
        fp_upper = cardinality_upper - n_true_positives
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^(([A-PR-UWYZ][0-9][0-9A-HJKPSTUW]?'
            r'|[A-PR-UWYZ][A-HK-Y][0-9][0-9ABEHMNPRVWXY]?'
            r'|[A-PR-UWYZ][0-9][A-HJKSTUW]'
            r'|[A-PR-UWYZ][A-HK-Y][0-9][ABEHMNPRVWXY]) '
            r'[0-9][ABD-HJLNP-VW-Z]{2}|GIR 0AA)$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=181,
            fp=CountRange(536_564_646, 857_083_446),
            fn=0,
            fpr=CountRange(
                0.00014863381053874586, 0.00023742074599648414
            ),
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_10_london_and_area_groups(self):
        # postcodes.txt group 10: London areas (with optional
        # subdistrict letter) and non-London areas (without), plus
        # GIR, NPT -- 4 branches in the embedded group, 2 of them
        # non-literal (London-shaped, area-list-shaped), so this
        # falls to the loose bound (2+ non-literal branches, same as
        # test_two_nonliteral_branches_unchanged).
        # London: 8 areas * 1-2 digits(110) * optional letter(1+26=27)
        london = 8 * 110 * 27  # 23_760
        # non-London: 116 areas * 1-2 digits(110)
        area_list = 116 * 110  # 12_760
        grp_lower = max(london, area_list, 1, 1)  # 23_760 (GIR/NPT=1 each)
        grp_upper = london + area_list + 1 + 1  # 36_522
        n_inward = 10 * 21**2  # 4_410
        cardinality_lower = grp_lower * n_inward
        cardinality_upper = grp_upper * n_inward
        n_true_positives = 55
        fp_lower = cardinality_lower - n_true_positives
        fp_upper = cardinality_upper - n_true_positives
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            '^((EC|WC|NW|SE|SW|E|N|W)[0-9]{1,2}[A-Z]?|(AB|AL|B|BA|'
            'BB|BD|BH|BL|BN|BR|BS|BT|CA|CB|CF|CH|CM|CO|CR|CT|CV|CW|'
            'DA|DD|DE|DG|DH|DL|DN|DT|DY|EH|EN|EX|FK|FY|G|GL|GU|GY|'
            'HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|IV|JE|KA|KT|KW|KY|L|'
            'LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|NE|NG|NN|NP|NR|OL|OX|'
            'PA|PE|PH|PL|PO|PR|RG|RH|RM|S|SA|SG|SK|SL|SM|SN|SO|SP|'
            'SR|SS|ST|SY|TA|TD|TF|TN|TQ|TR|TS|TW|UB|WA|WD|WF|WN|WR|'
            'WS|WV|YO|ZE)[0-9]{1,2}|GIR|NPT) '
            '[0-9][ABD-HJLNP-VW-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=430,
            fp=CountRange(104_781_545, 161_061_965),
            fn=0,
            fpr=CountRange(
                2.9025543191466766e-05, 4.461578631628316e-05
            ),
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_11_gir_handled_explicitly(self):
        # postcodes.txt group 11: as test_10, but GIR pulled out to
        # a separate top-level literal branch ('GIR 0AA'), removing
        # the over-acceptance test_10's comment flags. Inner group
        # is now (London|area-list|NPT) -- still 2 non-literal
        # branches, still a range -- combined with 'GIR 0AA' at the
        # outer level (disjoint by construction: different length/
        # inward shape).
        london = 8 * 110 * 27  # 23_760 (same as test_10)
        area_list = 116 * 110  # 12_760
        grp_lower = max(london, area_list, 1)  # NPT=1
        grp_upper = london + area_list + 1
        n_inward = 10 * 21**2  # 4_410
        inner_lower = grp_lower * n_inward
        inner_upper = grp_upper * n_inward
        cardinality_lower = 1 + inner_lower  # 'GIR 0AA'
        cardinality_upper = 1 + inner_upper
        n_true_positives = 55
        fp_lower = cardinality_lower - n_true_positives
        fp_upper = cardinality_upper - n_true_positives
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            '^(((EC|WC|NW|SE|SW|E|N|W)[0-9]{1,2}[A-Z]?|(AB|AL|B|BA|'
            'BB|BD|BH|BL|BN|BR|BS|BT|CA|CB|CF|CH|CM|CO|CR|CT|CV|CW|'
            'DA|DD|DE|DG|DH|DL|DN|DT|DY|EH|EN|EX|FK|FY|G|GL|GU|GY|'
            'HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|IV|JE|KA|KT|KW|KY|L|'
            'LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|NE|NG|NN|NP|NR|OL|OX|'
            'PA|PE|PH|PL|PO|PR|RG|RH|RM|S|SA|SG|SK|SL|SM|SN|SO|SP|'
            'SR|SS|ST|SY|TA|TD|TF|TN|TQ|TR|TS|TW|UB|WA|WD|WF|WN|WR|'
            'WS|WV|YO|ZE)[0-9]{1,2}|NPT) '
            '[0-9][ABD-HJLNP-VW-Z]{2}|GIR 0AA)$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=436,
            fp=CountRange(104_781_546, 161_057_556),
            fn=0,
            fpr=CountRange(
                2.9025543468476836e-05, 4.461456497888132e-05
            ),
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
        # count_strings now proves this directly (all branches are
        # distinct literals, hence pairwise disjoint by construction
        # -- see TestCountStringsDisjointAlternation), returning the
        # exact scalar 55 rather than a CountRange. (Before that was
        # added, cardinality came out as the imprecise CountRange(1,
        # 55), which relied on evaluate()'s fp-clamping -- fp.lower
        # = 1 - 55 = -54, clamped to 0 -- to reach the same fp=0
        # result; that clamping still exists as a safety net for
        # cases that remain imprecise, but isn't what's exercised
        # here any more.)
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

    def test_5_with_alternation(self):
        # The real postcodes.txt pattern 5, with its '|GIR|NPT'
        # alternation restored -- same shape as the E-subset version
        # of this test (alternation embedded in a larger sequence,
        # not the entire ^(...)$ body), handled by Plan B. Unlike
        # the E-subset (fn=0 either way), the full dataset actually
        # includes GIR/NPT-prefixed postcodes (special/reserved
        # codes, e.g. 'GIR 0AA', 'NPT 0AD') -- restoring the
        # alternation recovers exactly those 2_418 previously-missed
        # matches, taking fn to 0.
        n_letters = sum(26**k for k in range(1, 3))  # 702 (1-2 letters)
        n_digits = sum(10**k for k in range(1, 3))  # 110 (1-2 digits)
        n_trailing_letter = 27  # empty (1) + any of 26 letters
        general = n_letters * n_digits * n_trailing_letter  # 2_084_940
        n_inward = 10 * 26**2  # 6_760 (digit + 2 letters)
        # general outward codes, plus GIR/NPT, each paired with
        # every inward code: 2_084_940 * 6_760 + 2 * 6_760
        # = 14_094_194_400 + 13_520 = 14_094_207_920
        cardinality = general * n_inward + 2 * n_inward
        n_true_positives = 2_527_213
        fn = 0
        n_true_matched = n_true_positives - fn
        fp = cardinality - n_true_matched  # 14_091_680_707
        fp_denominator = self.q.universe - n_true_positives
        # fp_denominator: 3_609_974_530_250 (same as the
        # no-alternation version -- doesn't depend on the pattern)

        pattern = (
            r'^(GIR|NPT|[A-Z]{1,2}[0-9]{1,2}[A-Z]?) [0-9][A-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=52,
            fp=14_091_680_707,
            fn=0,
            fpr=0.0039035402019925373,
            fnr=0.0,
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

    def test_6_with_alternation(self):
        # postcodes.txt group 6 (the literal regex, not the
        # empirically-narrower test_6_valid_letters_only_no_alternation
        # above): letters restricted to those actually used anywhere,
        # GIR/NPT restored. Same formula as the E-subset version of
        # this test; fn=0 here too (GIR/NPT ARE present in the full
        # dataset, but this pattern explicitly covers them as
        # literal branches).
        general = 23 * 24 * 110 * 22  # 1_335_840 (see E-subset version)
        n_outward = general + 2  # 1_335_842
        n_inward = 10 * 21**2  # 4_410
        cardinality = n_outward * n_inward  # 5_891_063_220
        n_true_positives = 2_527_213
        fn = 0
        n_true_matched = n_true_positives - fn
        fp = cardinality - n_true_matched  # 5_888_536_007
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^([A-PR-UWYZ][A-HK-Y]?[0-9]{1,2}[A-HJKMNPR-VWXY]?'
            r'|GIR|NPT) [0-9][ABD-HJLNP-VW-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=84,
            fp=5_888_536_007,
            fn=0,
            fpr=0.0016311849176930907,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_7_explicit_area_codes(self):
        # postcodes.txt group 7: all 124 valid area codes listed
        # explicitly, plus GIR/NPT -- all disjoint literals, exact.
        # Same formula as the E-subset version; fn=0 (the 124-code
        # list is exhaustive over the real data too).
        n_areas = 124
        general = n_areas * 110 * 22  # 300_080
        n_outward = general + 2  # 300_082
        n_inward = 10 * 21**2  # 4_410
        cardinality = n_outward * n_inward  # 1_323_361_620
        n_true_positives = 2_527_213
        fn = 0
        n_true_matched = n_true_positives - fn
        fp = cardinality - n_true_matched  # 1_320_834_407
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            '^((AB|AL|B|BA|BB|BD|BH|BL|BN|BR|BS|BT|CA|CB|CF|CH|CM|'
            'CO|CR|CT|CV|CW|DA|DD|DE|DG|DH|DL|DN|DT|DY|E|EC|EH|EN|'
            'EX|FK|FY|G|GL|GU|GY|HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|'
            'IV|JE|KA|KT|KW|KY|L|LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|N|'
            'NE|NG|NN|NP|NR|NW|OL|OX|PA|PE|PH|PL|PO|PR|RG|RH|RM|S|'
            'SA|SE|SG|SK|SL|SM|SN|SO|SP|SR|SS|ST|SW|SY|TA|TD|TF|TN|'
            'TQ|TR|TS|TW|UB|W|WA|WC|WD|WF|WN|WR|WS|WV|YO|ZE)'
            '[0-9]{1,2}[A-HJKMNPR-VWXY]?|GIR|NPT) '
            '[0-9][ABD-HJLNP-VW-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=429,
            fp=1_320_834_407,
            fn=0,
            fpr=0.00036588468864031813,
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_8_government_transfer_spec(self):
        # postcodes.txt group 8 -- see the E-subset version of this
        # test for the source (UK government "Bulk Data Transfer"
        # spec PDF), the original mixed-case regex, and the
        # 200,000-candidate behavioral-equivalence check confirming
        # the uppercase-only, properly-nested version below matches
        # it exactly under fullmatch.
        #
        # 'GIR 0AA' literal plus 4 non-literal structural forms --
        # same 2+-non-literal-branch CountRange as the E-subset
        # version. fn=0: this pattern's form 4 has an *optional*
        # digit ([0-9]?), which is why NPT (letter-letter-letter, no
        # digit) still matches here, unlike test_9 below.
        b1 = 26 * 110  # 2_860
        b2 = 26 * 23 * 110  # 65_780
        b3 = 26 * 10 * 26  # 6_760
        b4 = 26 * 23 * 11 * 26  # 171_028
        grp_lower = max(b1, b2, b3, b4)
        grp_upper = b1 + b2 + b3 + b4
        n_inward = 10 * 26**2  # 6_760
        cardinality_lower = 1 + grp_lower * n_inward
        cardinality_upper = 1 + grp_upper * n_inward
        n_true_positives = 2_527_213
        fn = 0
        n_true_matched = n_true_positives - fn
        fp_lower = cardinality_lower - n_true_matched
        fp_upper = cardinality_upper - n_true_matched
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^(GIR 0AA|([A-Z][0-9]{1,2}|[A-Z][A-HJ-Y][0-9]{1,2}'
            r'|[A-Z][0-9][A-Z]|[A-Z][A-HJ-Y][0-9]?[A-Z]) '
            r'[0-9][A-Z]{2})$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=108,
            fp=CountRange(1_203_889_428, 1_732_927_028),
            fn=0,
            fpr=CountRange(
                0.00033348972905817913, 0.00048003857464334806
            ),
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_9_full_royal_mail_spec(self):
        # postcodes.txt group 9: same shape as test_8, tighter
        # letter classes. Unlike test_8's form 4, there's no
        # optional-digit form here -- every one of the 4 structural
        # forms requires exactly one digit. NPT (letter-letter-
        # letter, no digit) genuinely doesn't match any of them, so
        # fn=7084 (all 7_084 real NPT-prefixed postcodes) -- verified
        # directly two ways: `re.fullmatch` over the full dataset
        # here, and independently via ~/python/fAST/check_postcodes.py
        # (a pre-existing standalone script, polars `str.contains`
        # over a separately-loaded copy of the same data), which
        # reports 2,520,129 / 2,527,213 matched for this exact
        # pattern -- 2,527,213 - 2,520,129 = 7,084, confirming this
        # isn't a derivation error.
        c1 = 23 * 10 * (1 + 25)  # 5_980
        c2 = 23 * 23 * 10 * (1 + 22)  # 121_670
        c3 = 23 * 10 * 14  # 3_220
        c4 = 23 * 23 * 10 * 12  # 63_480
        grp_lower = max(c1, c2, c3, c4)
        grp_upper = c1 + c2 + c3 + c4
        n_inward = 10 * 21**2  # 4_410
        cardinality_lower = grp_lower * n_inward + 1  # 'GIR 0AA'
        cardinality_upper = grp_upper * n_inward + 1
        n_true_positives = 2_527_213
        fn = 7_084
        n_true_matched = n_true_positives - fn  # 2_520_129
        fp_lower = cardinality_lower - n_true_matched
        fp_upper = cardinality_upper - n_true_matched
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            r'^(([A-PR-UWYZ][0-9][0-9A-HJKPSTUW]?'
            r'|[A-PR-UWYZ][A-HK-Y][0-9][0-9ABEHMNPRVWXY]?'
            r'|[A-PR-UWYZ][0-9][A-HJKSTUW]'
            r'|[A-PR-UWYZ][A-HK-Y][0-9][ABEHMNPRVWXY]) '
            r'[0-9][ABD-HJLNP-VW-Z]{2}|GIR 0AA)$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=181,
            fp=CountRange(534_044_572, 854_563_372),
            fn=7_084,
            fpr=CountRange(
                0.0001479358282239781, 0.00023672282583689567
            ),
            fnr=0.00280308782837062,
        )
        self.assertTrue(score.eq(expected))

    def test_10_london_and_area_groups(self):
        # postcodes.txt group 10: London areas (optional subdistrict
        # letter) and non-London areas, plus GIR, NPT -- 2
        # non-literal branches in the embedded group, so a loose
        # bound, same shape as the E-subset version. fn=0: GIR and
        # NPT are both still explicit literal branches here.
        london = 8 * 110 * 27  # 23_760
        area_list = 116 * 110  # 12_760
        grp_lower = max(london, area_list, 1, 1)
        grp_upper = london + area_list + 1 + 1
        n_inward = 10 * 21**2  # 4_410
        cardinality_lower = grp_lower * n_inward
        cardinality_upper = grp_upper * n_inward
        n_true_positives = 2_527_213
        fn = 0
        n_true_matched = n_true_positives - fn
        fp_lower = cardinality_lower - n_true_matched
        fp_upper = cardinality_upper - n_true_matched
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            '^((EC|WC|NW|SE|SW|E|N|W)[0-9]{1,2}[A-Z]?|(AB|AL|B|BA|'
            'BB|BD|BH|BL|BN|BR|BS|BT|CA|CB|CF|CH|CM|CO|CR|CT|CV|CW|'
            'DA|DD|DE|DG|DH|DL|DN|DT|DY|EH|EN|EX|FK|FY|G|GL|GU|GY|'
            'HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|IV|JE|KA|KT|KW|KY|L|'
            'LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|NE|NG|NN|NP|NR|OL|OX|'
            'PA|PE|PH|PL|PO|PR|RG|RH|RM|S|SA|SG|SK|SL|SM|SN|SO|SP|'
            'SR|SS|ST|SY|TA|TD|TF|TN|TQ|TR|TS|TW|UB|WA|WD|WF|WN|WR|'
            'WS|WV|YO|ZE)[0-9]{1,2}|GIR|NPT) '
            '[0-9][ABD-HJLNP-VW-Z]{2}$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=430,
            fp=CountRange(102_254_387, 158_534_807),
            fn=0,
            fpr=CountRange(
                2.832551480437138e-05, 4.3915768843117314e-05
            ),
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))

    def test_11_gir_handled_explicitly(self):
        # postcodes.txt group 11: as test_10, but GIR pulled out to
        # a separate top-level literal branch. fn=0: NPT stays an
        # explicit literal branch inside the inner group.
        london = 8 * 110 * 27  # 23_760
        area_list = 116 * 110  # 12_760
        grp_lower = max(london, area_list, 1)  # NPT=1
        grp_upper = london + area_list + 1
        n_inward = 10 * 21**2  # 4_410
        inner_lower = grp_lower * n_inward
        inner_upper = grp_upper * n_inward
        cardinality_lower = 1 + inner_lower  # 'GIR 0AA'
        cardinality_upper = 1 + inner_upper
        n_true_positives = 2_527_213
        fn = 0
        n_true_matched = n_true_positives - fn
        fp_lower = cardinality_lower - n_true_matched
        fp_upper = cardinality_upper - n_true_matched
        fp_denominator = self.q.universe - n_true_positives

        pattern = (
            '^(((EC|WC|NW|SE|SW|E|N|W)[0-9]{1,2}[A-Z]?|(AB|AL|B|BA|'
            'BB|BD|BH|BL|BN|BR|BS|BT|CA|CB|CF|CH|CM|CO|CR|CT|CV|CW|'
            'DA|DD|DE|DG|DH|DL|DN|DT|DY|EH|EN|EX|FK|FY|G|GL|GU|GY|'
            'HA|HD|HG|HP|HR|HS|HU|HX|IG|IM|IP|IV|JE|KA|KT|KW|KY|L|'
            'LA|LD|LE|LL|LN|LS|LU|M|ME|MK|ML|NE|NG|NN|NP|NR|OL|OX|'
            'PA|PE|PH|PL|PO|PR|RG|RH|RM|S|SA|SG|SK|SL|SM|SN|SO|SP|'
            'SR|SS|ST|SY|TA|TD|TF|TN|TQ|TR|TS|TW|UB|WA|WD|WF|WN|WR|'
            'WS|WV|YO|ZE)[0-9]{1,2}|NPT) '
            '[0-9][ABD-HJLNP-VW-Z]{2}|GIR 0AA)$'
        )
        score = self.q.evaluate(pattern)
        expected = RexMetrics(
            len=436,
            fp=CountRange(102_254_388, 158_530_398),
            fn=0,
            fpr=CountRange(
                2.8325515081381648e-05, 4.391454750486047e-05
            ),
            fnr=0.0,
        )
        self.assertTrue(score.eq(expected))


if __name__ == '__main__':
    ReferenceTestCase.main()
