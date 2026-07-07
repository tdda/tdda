import os
import random
import time
import uuid

from tdda.rexpy.relib import re, reIsRegex

from tdda.referencetest import ReferenceTestCase, tag

from tdda.rexpy.testrexquality import POSTCODE_RE_4C, POSTCODE_RE_TIGHT3
from tdda.rexpy.xerpy import *


def check_xerpy(pattern, expected, weighted, n=8, N=1024):
    """Generate samples from `pattern` (with `weighted` passed to
    `Xerpy`), doubling the sample size (starting at `n`, capped at
    `N`) until every regex in `expected` has its observed match
    proportion inside its given `[low, high]` range, or `N` samples
    have been generated.

    Each regex in `expected` is checked independently -- a sample
    may fullmatch more than one (overlapping regexes are allowed,
    not treated as an error).

    Args:
        pattern (str): the regex to sample from.
        expected (dict): regex string -> [low, high] proportion
            range.
        weighted (bool): passed through to
            `Xerpy(pattern, weighted=...)`.
        n (int): initial sample size.
        N (int): sample size cap.

    Returns:
        tuple: (observed proportions dict, n samples drawn,
            ok bool -- whether every range was satisfied)
    """
    compiled = {r: re.compile(r) for r in expected}
    x = Xerpy(pattern, weighted=weighted)
    counts = {r: 0 for r in expected}
    drawn = 0
    target = n
    while True:
        while drawn < target:
            s = x.generate()
            for r, c in compiled.items():
                if c.fullmatch(s):
                    counts[r] += 1
            drawn += 1
        observed = {r: counts[r] / drawn for r in expected}
        ok = all(
            low <= observed[r] <= high
            for r, (low, high) in expected.items()
        )
        if ok or target >= N:
            break
        target = min(target * 2, N)
    return observed, drawn, ok


class TestXerpyWeighted(ReferenceTestCase):
    def test_equal_cardinality_branches(self):
        # true p=0.5 for each branch; [0.4, 0.6] at n=1024 alone
        # (the last doubling step) has a ~1.3e-10 chance of landing
        # outside that range by chance (exact binomial tail) -- an
        # upper bound on this test's false-failure rate, since it
        # can also succeed at any earlier checkpoint (8/16/.../512)
        expected = {'^a$': [0.4, 0.6]}
        for weighted in (False, True):
            observed, drawn, ok = check_xerpy(
                '(a|b)', expected, weighted=weighted,
            )
            self.assertTrue(ok, (weighted, observed, drawn))

    def test_unequal_cardinality_branches_unweighted(self):
        # 'a' (cardinality 1) vs '[c-z]' (cardinality 24): unweighted
        # picks each branch uniformly regardless, so still p=0.5
        expected = {'^a$': [0.4, 0.6]}
        observed, drawn, ok = check_xerpy(
            '(a|[c-z])', expected, weighted=False,
        )
        self.assertTrue(ok, (observed, drawn))

    def test_unequal_cardinality_branches_weighted(self):
        # weighted: true p('a') = 1/25 = 4%; [0.01, 0.10] at
        # N=2048 alone has a ~1.0e-16 chance of landing outside
        # that range by chance (exact binomial tail) -- an upper
        # bound on this test's false-failure rate, since it can
        # also succeed at any earlier checkpoint
        expected = {'^a$': [0.01, 0.10]}
        observed, drawn, ok = check_xerpy(
            '(a|[c-z])', expected, weighted=True, n=32, N=2048,
        )
        self.assertTrue(ok, (observed, drawn))

    def test_nested_alternation_unweighted(self):
        # unweighted picks uniformly at both levels: p('a')=0.5,
        # p('b')=0.25 (0.5 outer * 0.5 inner). Both ranges at
        # N=4096 alone have a chance of ~1.6e-14 ('a') / ~2.6e-18
        # ('b') of landing outside by chance (exact binomial tail)
        # -- upper bounds on this test's false-failure rate, since
        # it can also succeed at any earlier checkpoint. Ranges are
        # deliberately non-overlapping with the weighted case
        # below, since the true proportions genuinely differ.
        expected = {'^a$': [0.44, 0.56], '^b$': [0.19, 0.31]}
        observed, drawn, ok = check_xerpy(
            '(a|(b|c))', expected, weighted=False, n=32, N=4096,
        )
        self.assertTrue(ok, (observed, drawn))

    def test_nested_alternation_weighted(self):
        # weighted: 'a' has cardinality 1, '(b|c)' has cardinality
        # 2 (1 + 1), so p('a')=p('b')=1/3 (the inner 'b'/'c' split
        # is itself 1:1). [0.28, 0.39] at N=4096 alone has a
        # ~1.1e-13 chance of landing outside that range by chance
        # (exact binomial tail) for each -- an upper bound on this
        # test's false-failure rate, since it can also succeed at
        # any earlier checkpoint.
        expected = {'^a$': [0.28, 0.39], '^b$': [0.28, 0.39]}
        observed, drawn, ok = check_xerpy(
            '(a|(b|c))', expected, weighted=True, n=32, N=4096,
        )
        self.assertTrue(ok, (observed, drawn))

    # POSTCODE_RE_TIGHT3's outward code is a 3-way alternation
    # (general area/digit shape | NPT | GIR) whose true cardinality
    # shares (computed directly from the parsed Group tree, not by
    # hand) are 61_280_000 : 4_200 : 1 out of 61_284_201 total --
    # wildly unequal. Within the general shape, London (8 areas)
    # vs non-London (~100 areas) split 10_240_000 : 51_040_000.
    #
    # Within London, the digit-part is itself an alternation
    # ('[0-9][A-HJKMNPR-VWXY]?' vs '[0-9]{2}', cardinality 220 vs
    # 100 -- correctly cardinality-weighted), but the trailing
    # subdistrict letter within the first branch is an optional
    # quantifier ('?'), not a further alternation -- its own
    # present/absent choice is always a uniform 50/50 draw,
    # regardless of `weighted` (that flag only reweights alternation
    # branch choice, not a quantifier's repeat count). So
    # P(subdistrict letter | London) = P(digit+letter branch) * 0.5,
    # giving 0.5*0.5=0.25 unweighted and 0.6875*0.5=0.34375 weighted
    # -- confirmed against direct sampling before finalizing these
    # numbers, since naively treating branch cardinality as if it
    # were the letter's own presence probability (220/320=0.6875)
    # was wrong by a factor of 2 in an earlier version of this test.
    NPT_RE = r'^NPT .*$'
    GIR_RE = r'^GIR 0AA$'
    GENERAL_RE = r'^(?!GIR |NPT ).*$'
    LONDON_RE = r'^(?:EC|WC|NW|SE|SW|E|N|W)[0-9].*$'
    LONDON_SUBDISTRICT_RE = (
        r'^(?:EC|WC|NW|SE|SW|E|N|W)[0-9][A-HJKMNPR-VWXY] .*$'
    )

    def test_tight3_branches_unweighted(self):
        # unweighted: uniform at every alternation point regardless
        # of cardinality -- 1/3 each for GIR/NPT/general, 1/6 for
        # London (1/3 general * 1/2 London-vs-not), 1/24 for
        # London-with-subdistrict (1/6 London * 1/2 branch * 1/2
        # quantifier). London's true weighted share (16.71%) happens
        # to coincide almost exactly with unweighted's 1/6 (16.67%)
        # here -- a coincidence of this particular pattern's
        # cardinalities, not a general property -- so that check
        # alone wouldn't distinguish the two modes; the
        # subdistrict-letter split (1/24=4.17% here vs 5.74%
        # weighted) does, though only modestly, since the quantifier
        # draw dilutes the underlying cardinality difference.
        expected = {
            self.GIR_RE: [0.28, 0.39],
            self.NPT_RE: [0.28, 0.39],
            self.GENERAL_RE: [0.28, 0.39],
            self.LONDON_RE: [0.13, 0.21],
            self.LONDON_SUBDISTRICT_RE: [0.033, 0.047],
        }
        observed, drawn, ok = check_xerpy(
            POSTCODE_RE_TIGHT3, expected, weighted=False,
            n=128, N=65536,
        )
        self.assertTrue(ok, (observed, drawn))

    def test_tight3_branches_weighted(self):
        # weighted: GIR (~1.6e-8) and NPT (~6.85e-5) are both
        # essentially never seen; general is ~99.993%; London is
        # ~16.71% (see the unweighted test's coincidence note); the
        # subdistrict-letter split is ~5.74%, genuinely apart from
        # unweighted's 4.17% (see the class comment above on why
        # this isn't simply 220/320=68.75%).
        expected = {
            self.GIR_RE: [0, 1e-4],
            self.NPT_RE: [0, 0.01],
            self.GENERAL_RE: [0.99, 1.0],
            self.LONDON_RE: [0.13, 0.21],
            self.LONDON_SUBDISTRICT_RE: [0.050, 0.065],
        }
        observed, drawn, ok = check_xerpy(
            POSTCODE_RE_TIGHT3, expected, weighted=True,
            n=128, N=65536,
        )
        self.assertTrue(ok, (observed, drawn))

    # POSTCODE_RE_4C is a simpler contrast to TIGHT3: a flat 3-way
    # alternation (GIR | NPT | general shape) with no further
    # nesting -- cardinalities (confirmed via the parsed Group tree)
    # are 1 : 1 : 259_740 out of 259_742 total. Unlike TIGHT3's GIR,
    # this pattern's inward code isn't fixed to '0AA' (it's the
    # general '[0-9][A-Z]{2}'), so GIR/NPT are matched by prefix only.
    RE4C_GIR_RE = r'^GIR .*$'
    RE4C_NPT_RE = r'^NPT .*$'
    RE4C_GENERAL_RE = r'^(?!GIR |NPT ).*$'

    def test_4c_branches_unweighted(self):
        # unweighted: 1/3 each, regardless of the general branch's
        # true 259_740-to-1 cardinality advantage over GIR/NPT
        expected = {
            self.RE4C_GIR_RE: [0.28, 0.39],
            self.RE4C_NPT_RE: [0.28, 0.39],
            self.RE4C_GENERAL_RE: [0.28, 0.39],
        }
        observed, drawn, ok = check_xerpy(
            POSTCODE_RE_4C, expected, weighted=False, n=32, N=4096,
        )
        self.assertTrue(ok, (observed, drawn))

    def test_4c_branches_weighted(self):
        # weighted: true p(GIR)=p(NPT)=1/259_742 (~3.85e-6, so
        # essentially never seen even at N=65536, where the expected
        # count is only ~0.25); general is ~99.9992%
        expected = {
            self.RE4C_GIR_RE: [0, 1e-4],
            self.RE4C_NPT_RE: [0, 1e-4],
            self.RE4C_GENERAL_RE: [0.99, 1.0],
        }
        observed, drawn, ok = check_xerpy(
            POSTCODE_RE_4C, expected, weighted=True, n=128, N=65536,
        )
        self.assertTrue(ok, (observed, drawn))


class TestXerpy(ReferenceTestCase):
    def test_get_number(self):
        x = Xerpy('')
        self.assertRaisesRegex(Exception, 'Expected digit',
                               x.get_number, 0)

        x = Xerpy('.')
        self.assertRaises(ValueError, x.get_number, 0)

        x = Xerpy('0.23.5678')
        self.assertEqual(x.get_number(0), (0, 1))
        self.assertEqual(x.get_number(2), (23, 4))
        self.assertEqual(x.get_number(3), (3, 4))  # probably wouldn't do this
        self.assertEqual(x.get_number(5), (5678, 9))

        for p in (1, 4):
            self.assertRaises(ValueError, x.get_number, p)

    def test_get_any_quantifier_none_there(self):
        x = Xerpy('')
        self.assertEqual(x.get_any_quantifier(0), (quantifier(None), 0))

        x = Xerpy('.')
        self.assertEqual(x.get_any_quantifier(0), (quantifier(None), 0))

    def test_get_star_quantifier(self):
        x = Xerpy('.*')
        self.assertEqual(x.get_any_quantifier(0), (quantifier(None), 0))
        self.assertEqual(x.get_any_quantifier(1), (quantifier(0, None), 2))

    def test_get_plus_quantifier(self):
        x = Xerpy('.+')
        self.assertEqual(x.get_any_quantifier(0), (quantifier(None), 0))
        self.assertEqual(x.get_any_quantifier(1), (quantifier(1, None), 2))

    def test_get_query_quantifier(self):
        x = Xerpy('.?')
        self.assertEqual(x.get_any_quantifier(0), (quantifier(None), 0))
        self.assertEqual(x.get_any_quantifier(1), (quantifier(0, 1), 2))

    def test_get_any_quantifier_out_of_range(self):
        x = Xerpy('')
        self.assertRaisesRegex(Exception, 'Expected digit', x.get_number, 1)

    def test_get_any_quantifier_single(self):
        x = Xerpy('{1}..{66}.')
        self.assertEqual(x.get_any_quantifier(0), (quantifier(1, 1), 3))
        self.assertEqual(x.get_any_quantifier(5), (quantifier(66, 66), 9))

    def test_get_any_quantifier_multiple(self):
        x = Xerpy('0.{3,5}..{10,13}..')
        for p in (0, 1, 3):
            self.assertEqual(x.get_any_quantifier(p), (quantifier(None), p))

        self.assertEqual(x.get_any_quantifier(2), (quantifier(3, 5), 7))
        self.assertEqual(x.get_any_quantifier(9), (quantifier(10, 13), 16))

    def test_unfinished_quantifier(self):
        x = Xerpy('{3,')
        self.assertRaisesRegex(Exception,
                               'Regular expression terminated',
                               x.get_any_quantifier, 0)
        x = Xerpy('..{3,4')
        self.assertRaisesRegex(Exception,
                               'Regular expression terminated',
                               x.get_any_quantifier, 2)

    def test_quantifier_const(self):
        q = quantifier(3, 3)
        for i in range(3):
            self.assertEqual(q(), 3)

        q = quantifier(12, 12)
        for i in range(3):
            self.assertEqual(q(), 12)

    def test_quantifier_range(self):
        q = quantifier(2, 5)
        vals = set()
        for i in range(100):
            p = q()
            vals.add(p)
            self.assertTrue(2 <= p <= 5)
        self.assertTrue(len(vals) > 1)  # probabilistically.
                                        # but really should pass!

    def test_quantifier_range(self):
        q = quantifier(0, None)
        vals = set()
        for i in range(100):
            p = q()
            vals.add(p)
            self.assertTrue(0 <= p <= 100)
        self.assertTrue(len(vals) > 1)
        # more probabilistic tests

    def test_quantifier_range(self):
        q = quantifier(1, None)
        vals = set()
        for i in range(100):
            p = q()
            vals.add(p)
            self.assertTrue(1 <= p <= 100)
        self.assertTrue(len(vals) > 1)
        # more probabilistic tests

    def test_empty(self):
        R = r'^$'
        for i in range(3):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))

    def test_dot(self):
        Ref = r'^.$'
        for R in (Ref, r'^\p{Any}$', r'^\p{any}$'):
            for i in range(3):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_dotdot(self):
        Ref = r'^..$'
        for R in (Ref, r'^\p{Any}.$', r'^.\p{Any}$', r'^\p{Any}\p{any}$'):
            for i in range(3):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_dot_3(self):
        Ref = r'^.{3}$'
        for R in (Ref, r'^\p{Any}{3}$'):
            for i in range(3):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_dot_24(self):
        Ref = r'^.{2,4}$'
        for R in (Ref, r'^\p{Any}{2,4}$'):
            for i in range(5):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_dot_plus(self):
        Ref = r'^.+$'
        for R in (Ref, r'^\p{Any}+$'):
            for i in range(5):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_dot_star(self):
        Ref = r'^.*$'
        for R in (Ref, r'^\p{Any}*$'):
            for i in range(5):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_get_brackets(self):
        x = Xerpy('[a]')
        x.compile()
        self.assertEqual(x.generators[0], (brackets(('a',)), quantifier(None)))

        x = Xerpy('[a-cA0-2]')
        x.compile()
        self.assertEqual(x.generators[0], (brackets(tuple(list('012Aabc'))),
                                           quantifier(None)))

        x = Xerpy('[a-c0-2]')
        x.compile()
        self.assertEqual(x.generators[0], (brackets(tuple(list('012abc'))),
                                           quantifier(None)))

        x = Xerpy('[Aa-cB0-2C]')
        x.compile()
        self.assertEqual(x.generators[0], (brackets(tuple(list('012ABCabc'))),
                                           quantifier(None)))

        x = Xerpy('[^!-z]')
        x.compile()
        chars = BEFORE_BANG + AFTER_z
        self.assertEqual(x.generators[0], (brackets(tuple(list(chars))),
                                           quantifier(None)))

    def test_simple_brackets(self):
        R = r'^[a]$'
        x = Xerpy(R)
        self.assertIsNotNone(re.match(R, x.generate()))

        R = r'^[bbb]{2}$'
        x = Xerpy(R)
        self.assertIsNotNone(re.match(R, x.generate()))

        R = r'^[abcdefghij]{3,3}$'
        vals = set()
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertTrue(len(vals) > 1)

        R = r'^[abc]{1,5}$'
        for i in range(10):
            x = Xerpy(R)
            self.assertIsNotNone(re.match(R, x.generate()))

    def test_uuid_brackets_with_escapes(self):
        RD = r'[\da-f]'
        Ref = r'^%s{8}\-%s{4}\-%s{4}\-%s{4}\-%s{12}$' % (RD, RD, RD, RD, RD)
        for X in (RD, r'[[:digit:]a-f]', r'[\p{Digit}a-f]'):
            R = r'^%s{8}\-%s{4}\-%s{4}\-%s{4}\-%s{12}$' % (X, X, X, X, X)
            for i in range(10):
                x = Xerpy(R)
                u = x.generate()
                self.assertIsNotNone(re.match(Ref, u))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, u))
                U = uuid.UUID(u)  # no error; is a UUID!

    def test_mixed_uuid_brackets_with_escapes(self):
        RD = r'[\da-fA-F]'
        Ref = r'^%s{8}\-%s{4}\-%s{4}\-%s{4}\-%s{12}$' % (RD, RD, RD, RD, RD)
        for X in (RD, r'[[:xdigit:]]', r'\p{XDigit}', r'\p{Hex_Digit}'):
            R = r'^%s{8}\-%s{4}\-%s{4}\-%s{4}\-%s{12}$' % (X, X, X, X, X)
            for i in range(10):
                x = Xerpy(R)
                u = x.generate()
                self.assertIsNotNone(re.match(Ref, u))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, u))
                U = uuid.UUID(u)  # no error; is a UUID!

    def test_brackets_with_simple_escapes(self):
        Ref = r'^a[\ts\$]z[\s]{2}$'
        for R in (Ref, r'^a[\ts\$]z[[:space:]]{2}$',
                  r'^a[\ts\$]z[\p{Space}]{2}$'):
            for i in range(10):
                x = Xerpy(R)
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))

    def test_range_bracket(self):
        R = r'^[a-e]{10}'
        vals = set()
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertTrue(len(vals) > 1)

    def test_exclusion_range_bracket(self):
        R = r'^[^!-z]{10}'
        vals = set()
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertTrue(len(vals) > 1)

    def test_multi_exclusion_range_bracket(self):
        R = r'^[^ -146-~]{10}'
        vals = set()
        for i in range(20):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertTrue(len(vals) > 1)
        chars = set(list(''.join(sorted(vals))))
        self.assertEqual(chars, set(list('235')))  # Exactly right chars used

    def test_bracket_leading_close_literal(self):
        # ']' as the first character of a class is a literal member,
        # not the closing bracket -- the class only closes at the
        # *next* ']'.
        R = r'^[]a]$'
        vals = set()
        for i in range(20):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertEqual(vals, {']', 'a'})

    def test_bracket_leading_dash_literal(self):
        # '-' as the first character of a class is a literal, not a
        # range operator.
        R = r'^[-a]$'
        vals = set()
        for i in range(20):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertEqual(vals, {'-', 'a'})

    def test_bracket_trailing_dash_literal(self):
        # '-' as the last character of a class is a literal, not a
        # range operator.
        R = r'^[a-]$'
        vals = set()
        for i in range(20):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertEqual(vals, {'-', 'a'})

    def test_bracket_leading_dash_after_exclusion_literal(self):
        # '-' immediately after the exclusion '^' is a literal, not a
        # range operator.
        R = r'^[^-a]{5}$'
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            self.assertNotIn('-', s)
            self.assertNotIn('a', s)

    def test_bracket_leading_close_literal_after_exclusion(self):
        # ']' immediately after the exclusion '^' is a literal, not
        # the closing bracket -- combines the leading-']'-is-literal
        # fix with negation.
        R = r'^[^]a]{5}$'
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            self.assertNotIn(']', s)
            self.assertNotIn('a', s)

    def test_bracket_excludes_everything(self):
        # Negating the whole alphabet xerpy uses leaves nothing to
        # generate from -- must raise a clear error, not silently
        # produce nothing or crash some other way.
        self.assertRaisesRegex(Exception, 'excludes everything',
                               Xerpy(r'^[^ -~]$').generate)

    def test_bracket_hex_digits_with_trailing_dash(self):
        # Realistic case combining a range with a trailing literal
        # '-', as in a UUID-without-hyphens-or-with pattern.
        R = r'^[0-9a-fA-F-]{32,36}$'
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))

    def test_fixed(self):
        R = r'^a$'
        x = Xerpy(R)
        s = x.generate()
        self.assertEqual(s, 'a')
        self.assertIsNotNone(re.match(R, s))

        R = r'^ab{3}'
        x = Xerpy(R)
        s = x.generate()
        self.assertEqual(s, 'abbb')
        self.assertIsNotNone(re.match(R, s))

        R = r'^a{2}b{3}'
        x = Xerpy(R)
        s = x.generate()
        self.assertEqual(s, 'aabbb')
        self.assertIsNotNone(re.match(R, s))

    def test_escape_d(self):
        Ref = r'^\d{10}$'
        for R in (Ref, r'^[[:digit:]]{10}$', r'^\p{Number}{10}$',
                  r'^[0-9]{10}$'):
            x = Xerpy(R)
            vals = set()
            for i in range(10):
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))
                vals.add(s)
            self.assertTrue(len(vals) > 1)

    def test_escape_w(self):
        Ref = r'^\w{5}$'
        for R in (Ref, r'^\p{Word}{5}$', r'^\P{^Word}{5}$'):
            x = Xerpy(R)
            vals = set()
            for i in range(10):
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))
                vals.add(s)
            self.assertTrue(len(vals) > 1)

    def test_escape_W(self):
        Ref = r'^\W{5}$'
        for R in (Ref, r'^\p{^Word}{5}$', r'^\P{Word}{5}$'):
            x = Xerpy(R)
            vals = set()
            for i in range(10):
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))
                vals.add(s)
            self.assertTrue(len(vals) > 1)

    def test_inverse_any(self):
        x = Xerpy(r'\P{Any}')
        self.assertRaisesRegex(Exception, 'Cannot invert Any', x.generate)
        x = Xerpy(r'\p{^Any}')
        self.assertRaisesRegex(Exception, 'Cannot invert Any', x.generate)

    def test_escape_s(self):
        Ref = r'^\s{10}$'
        for R in (r'^\s{10}$', r'^[[:space:]]{10}$', r'^\p{Space}{10}$'):
            x = Xerpy(R)
            vals = set()
            for i in range(10):
                s = x.generate()
                self.assertIsNotNone(re.match(Ref, s))
                if reIsRegex:
                    self.assertIsNotNone(re.match(R, s))
                vals.add(s)
            self.assertTrue(len(vals) > 1)

    def test_singleton_escapes(self):
        R = r'\$\t\[\r\]\n\^\f\-\v\\$'
        self.assertEqual(Xerpy(R).generate(), '$\t[\r]\n^\f-\v\\')
        R = r'\${2}\t{3}\[\r\]\n\^\f\-\v\\{4}$'
        self.assertEqual(Xerpy(R).generate(), '$$\t\t\t[\r]\n^\f-\v\\\\\\\\')

    def test_alternation(self):
        R = '^ab(cc|dd){4}(e|f){4,6}z$'
        x = Xerpy(R)
        vals = set()
        for i in range(10):
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))
            vals.add(s)
        self.assertTrue(len(vals) > 1)

    def test_nested_optional_group(self):
        # An optional group containing another optional group.
        # Bug: RootGroup.push() sets every group's parent to the root
        # container instead of the actual enclosing group, so closing
        # the inner group pops all the way back to root, and the
        # outer group's closing ')' then finds nothing open.
        R = r'^(a(b)?)?$'
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))

    def test_nested_group_inside_alternation(self):
        # A nested group inside one branch of an outer alternation.
        # Same root cause as test_nested_optional_group, surfaced as a
        # different error ("Alternation marker '|' found outside
        # group") because the next token after the wrongly-popped
        # group happens to be '|' rather than ')'.
        R = r'^(aa|a(bb|cc)|dd)$'
        for i in range(10):
            x = Xerpy(R)
            s = x.generate()
            self.assertIsNotNone(re.match(R, s))

    def test_toplevel_alternation(self):
        # A '|' outside any explicit group, applying to the whole
        # pattern. xerpy treats this as if the anchor-stripped body
        # were wrapped in a group (as if the pattern were
        # '^(aa|bb)$'), since that is the only sensible generative
        # reading: xerpy always generates a complete string for the
        # whole pattern rather than searching for a match within a
        # larger one, so there is no meaningful generative difference
        # between '^aa|bb$' and '^(aa|bb)$', unlike for
        # re.search/re.match (where the unwrapped form means '^aa' or
        # 'bb$', each with only one of the two anchors).
        R = r'^aa|bb$'
        vals = set()
        for i in range(20):
            s = Xerpy(R).generate()
            self.assertIn(s, ('aa', 'bb'))
            vals.add(s)
        self.assertEqual(vals, {'aa', 'bb'})

    def test_toplevel_alternation_escaped_trailing_dollar(self):
        # A '|' triggers wrapping, but the pattern's trailing '$' is
        # an escaped literal, not a real anchor, and must not be
        # stripped and reattached as one.
        R = r'a|b\$'
        vals = set()
        for i in range(20):
            s = Xerpy(R).generate()
            self.assertIn(s, ('a', 'b$'))
            vals.add(s)
        self.assertEqual(vals, {'a', 'b$'})

    def test_toplevel_alternation_escaped_leading_caret(self):
        # Same as above but for a leading escaped '^', which is a
        # literal, not a real anchor.
        R = r'\^a|b$'
        vals = set()
        for i in range(20):
            s = Xerpy(R).generate()
            self.assertIn(s, ('^a', 'b'))
            vals.add(s)
        self.assertEqual(vals, {'^a', 'b'})

    def test_error_position_reported_in_original_coordinates(self):
        # A malformed pattern that also contains a '|', so it gets
        # wrapped internally in a synthetic group. The reported error
        # position (and displayed snippet) must refer to the user's
        # original string, not the internally-wrapped one.
        R = r'a|[z-a]'
        self.assertRaisesRegex(Exception, r'\(position 5\)',
                               Xerpy(R).generate)

    def test_error_position_past_synthetic_close_paren(self):
        # An unmatched inner '(': the pattern's one and only ')'
        # closes the inner group instead of the synthetic outer one,
        # so the "unbalanced parentheses" error fires at end-of-string
        # in the wrapped pattern's coordinates, past the synthetic
        # close paren -- exercising the other branch of map_position
        # from test_error_position_reported_in_original_coordinates
        # above (which only ever lands before the synthetic close
        # paren).
        R = r'a|(b'
        self.assertRaisesRegex(Exception, r'\(position 4\)',
                               Xerpy(R).generate)

    def multi_regex_xerpy_test(self, filename, min_tested):
        """
        Reads regexes from testdata/filename (one per line, blank
        lines and lines starting '#' ignored) and, for each one,
        checks that generating five examples doesn't raise and that
        every example actually matches the regex. min_tested is a
        sanity check that the file wasn't accidentally truncated or
        misnamed.
        """
        path = os.path.join(os.path.dirname(__file__),
                            'testdata', filename)
        with open(path) as f:
            lines = f.readlines()

        tested = 0
        for line in lines:
            pattern = line.strip()
            if not pattern or pattern.startswith('#'):
                continue
            for i in range(5):
                s = Xerpy(pattern).generate()
                self.assertIsNotNone(re.match(pattern, s))
            tested += 1
        self.assertGreater(tested, min_tested)

    def test_postcode_regexes(self):
        # A real-world regex corpus: the tdda project's UK postcode
        # progression (loose bound -> full Royal Mail spec), copied
        # from fAST/postcodes.txt.
        self.multi_regex_xerpy_test('postcode-regexes.txt', 5)

    def test_fAST_example_regexes(self):
        # A second, independent real-world "progressive" regex corpus
        # (loose bound -> full validator), covering IPv4, UK car
        # registrations, UK NI numbers, UK phone numbers, ISBN, UUIDs,
        # datetimes, and Chinese ID numbers. Derived from the fAST
        # project's finite_regex_examples_fixed.txt (see
        # ~/python/fAST), an independently-authored corpus not written
        # with xerpy's own test coverage in mind, so it's a useful
        # check that xerpy holds up against regex shapes we didn't
        # think to construct ourselves -- in particular nested and
        # sibling alternation groups (e.g. the CHN id number
        # patterns), which is what motivated the RootGroup
        # parent-pointer fix elsewhere in this file.
        self.multi_regex_xerpy_test('xerpy-test-regexes.txt', 30)

    def test_misplaced_anchor_error_message(self):
        # Bug: start_anchor/end_anchor call self.error(msg) without
        # the required 'p' argument, so a misplaced '^' or '$' raises
        # a broken TypeError ("missing 1 required positional
        # argument: 'p'") instead of the intended, informative
        # message.
        self.assertRaisesRegex(Exception,
                               'Unescaped \\^ can only occur at the start',
                               Xerpy('a^b').generate)
        self.assertRaisesRegex(Exception,
                               'Unescaped \\$ can only occur at the end',
                               Xerpy('^abc$ stray text').generate)

    def test_anchors_are_literal_inside_character_class(self):
        # '^' and '$' inside a character class are ordinary literal
        # characters (bracket() consumes the whole class directly,
        # without ever routing through start_anchor/end_anchor), so
        # the "can only occur at start/end" restriction genuinely
        # doesn't apply there.
        for i in range(20):
            self.assertIn(Xerpy(r'^[a^b]$').generate(), ('a', '^', 'b'))
            self.assertIn(Xerpy(r'^[a$b]$').generate(), ('a', '$', 'b'))

    def test_length_increase(self):
        R = 'a{2,5}b{3,6}'
        x = Xerpy(R)
        a = [len(x.generate(10,15)) for i in range(10)]
        self.assertTrue(all(10 <= n <= 11 for n in a))

    def test_length_reduction(self):
        R = 'a{2,5}b{3,6}'
        x = Xerpy(R)
        a = [len(x.generate(1, 7)) for i in range(10)]
        self.assertTrue(all(5 <= n <= 7 for n in a))

    def test_length_clamping(self):
        R = 'a{2,5}b{3,6}'
        x = Xerpy(R)
        a = [x.generate(6, 6) for i in range(10)]
        self.assertTrue(all(len(s) == 6 for s in a))


if __name__ == '__main__':
    t = int(time.time())
    random.seed(t)
    print('Seed: %s' % t)
    ReferenceTestCase.main()
