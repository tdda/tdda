# -*- coding: utf-8 -*-

"""
Tests for tdda.rexpy.quality
"""

from tdda.referencetest import ReferenceTestCase, tag

from tdda.rexpy.quality import (
    Alphabets,
    CountRange,
    DIGIT_CHARS,
    Repeat,
    WHITESPACE_CHARS,
    count_strings,
    count_strings_no_alt,
    _as_range,
    _atom_size,
    _charclass_members,
    _check_subset,
    _escape_size,
    _matching_paren,
    _parse_pattern,
    _parse_quantifier,
    _split_alternation,
    _split_top_level,
    _validate_pattern,
)


class TestAlphabets(ReferenceTestCase):
    def test_ascii(self):
        self.assertEqual(len(Alphabets.ASCII), 128)
        self.assertEqual(Alphabets.ASCII[0], chr(0))
        self.assertEqual(Alphabets.ASCII[-1], chr(127))


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


class TestCheckSubset(ReferenceTestCase):
    # The four ways `chars` (what the pattern references) and
    # `alphabet` (what's allowed) can relate: only a proper subset
    # or exact match should pass; every other relationship (partial
    # overlap, disjoint, or `chars` being a strict superset of
    # `alphabet`) should raise.

    def test_accepts_exact_match(self):
        _check_subset('abc', 'abc', '^[abc]$')  # no exception

    def test_accepts_proper_subset(self):
        _check_subset('abc', 'abcdef', '^[abc]$')  # no exception

    def test_rejects_partial_overlap(self):
        # 'a' is in chars but not alphabet; 'd' is in alphabet but
        # not chars -- neither is a subset of the other
        self.assertRaises(
            ValueError, _check_subset, 'abc', 'bcd', '^[a-c]$'
        )

    def test_rejects_disjoint(self):
        self.assertRaises(
            ValueError, _check_subset, 'abc', 'xyz', '^[abc]$'
        )

    def test_rejects_chars_superset_of_alphabet(self):
        # alphabet is a proper subset of chars, but chars has
        # members ('d' onwards) outside alphabet too
        self.assertRaises(
            ValueError, _check_subset, 'abcdefgh', 'abc', '^[a-h]$'
        )


class TestEscapeSize(ReferenceTestCase):
    def test_dot(self):
        self.assertEqual(_escape_size('.', Alphabets.ASCII, '^.$'), 128)

    def test_dot_custom_alphabet(self):
        self.assertEqual(_escape_size('.', 'abc', '^.$'), 3)

    def test_digit(self):
        self.assertEqual(_escape_size('d', Alphabets.ASCII, r'^\d$'), 10)

    def test_non_digit(self):
        self.assertEqual(
            _escape_size('D', Alphabets.ASCII, r'^\D$'), 128 - 10
        )

    def test_word(self):
        self.assertEqual(_escape_size('w', Alphabets.ASCII, r'^\w$'), 63)

    def test_non_word(self):
        self.assertEqual(
            _escape_size('W', Alphabets.ASCII, r'^\W$'), 128 - 63
        )

    def test_whitespace(self):
        self.assertEqual(_escape_size('s', Alphabets.ASCII, r'^\s$'), 6)

    def test_non_whitespace(self):
        self.assertEqual(
            _escape_size('S', Alphabets.ASCII, r'^\S$'), 128 - 6
        )

    def test_raises_if_canonical_members_outside_alphabet(self):
        # alphabet has no digits at all, but \d needs them
        self.assertRaises(ValueError, _escape_size, 'd', 'abc', r'^\d$')

    def test_non_digit_small_custom_alphabet(self):
        # digits plus one extra char: \D is just that extra char
        self.assertEqual(
            _escape_size('D', DIGIT_CHARS + ' ', r'^\D$'), 1
        )

    def test_non_whitespace_small_custom_alphabet(self):
        self.assertEqual(
            _escape_size('S', WHITESPACE_CHARS + 'abc', r'^\S$'), 3
        )

    def test_word_raises_when_alphabet_missing_uppercase(self):
        # canonical \w needs uppercase letters too, which this
        # alphabet doesn't have
        alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789'
        self.assertRaises(ValueError, _escape_size, 'w', alphabet, r'^\w$')


class TestAtomSize(ReferenceTestCase):
    def test_literal(self):
        self.assertEqual(
            _atom_size('literal', 'a', Alphabets.ASCII, '^a$'), 1
        )

    def test_literal_outside_alphabet(self):
        self.assertRaises(
            ValueError, _atom_size, 'literal', 'a', '012', '^a$'
        )

    def test_bracket(self):
        self.assertEqual(
            _atom_size('charclass', '[A-Z]', Alphabets.ASCII, '^[A-Z]$'),
            26,
        )

    def test_negated_bracket(self):
        self.assertEqual(
            _atom_size(
                'charclass', '[^A-Z]', Alphabets.ASCII, '^[^A-Z]$'
            ),
            128 - 26,
        )

    def test_dot(self):
        self.assertEqual(
            _atom_size('charclass', '.', Alphabets.ASCII, '^.$'), 128
        )

    def test_escape(self):
        self.assertEqual(
            _atom_size('charclass', r'\d', Alphabets.ASCII, r'^\d$'), 10
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
        self.assertEqual(count_strings_no_alt('^[A-Z]{2,}$', max_plus=3), 18252)

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
        self.assertEqual(count_strings_no_alt('^.$'), 128)

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


if __name__ == '__main__':
    ReferenceTestCase.main()
