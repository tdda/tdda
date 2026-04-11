import datetime
import numpy as np
import os
import tempfile
import unicodedata

from tdda.referencetest.referencetestcase import ReferenceTestCase, tag
from tdda.utils import (
    to_pc,
    n_glyphs,
    handle_tilde,
    XML,
    squote,
    DQuote,
    tddadir,
    Dummy,
    swap_ext,
    dict_to_json,
    dict_to_toml,
    dict_to_yaml,
    json_sanitize,
    swap_ext_q,
    CONSTRAINTSDIR,
    PDCONSTRAINTSDIR,
    normal_form_tk,
    is_sequence,
    listify,
    globlike_match,
    tex_name,
    tex_encode,
)
from unicodedata import normalize

TMPDIR = tempfile.mkdtemp()
TESTDIR = os.path.join(os.path.dirname(__file__), 'testdata')


class TestTDDAUtils(ReferenceTestCase):
    def test_to_pc(self):
        cases = {
            (1, 1): '100.00%',
            (0, 1): '0.00%',
            (99, 100): '99.00%',
            (1, 100): '1.00%',
            (3, 9): '33.33%',
            (1, 37): '2.70%',
            (9_999, 10_000): '99.99%',
            (1, 10_000): '0.01%',
            (19_999, 20_001): '99.99%',
            (19_999, 20_000): '99.995%',
            (1, 19_999): '0.01%',
            (1, 20_000): '0.01%',
            (99_999, 100_000): '99.999%',
            (1, 100_000): '0.001%',
            (199_999, 200_001): '99.999%',
            (199_999, 200_000): '99.999%',
            (1, 199_999): '0.001%',
            (1, 200_000): '0.001%',
            (999_999, 1_000_000): '99.9999%',
            (1, 1_000_000): '0.0001%',
            (999_999_999, 1_000_000_000): '99.9999999%',
            (1_999_999_999, 2_000_000_000): '99.9999999%',
            (3_999_999_999, 4_000_000_000): '99.99999997%',
            (1, 1_000_000_000): '0.0000001%',
            (1, 2_000_000_000): '0.0000001%',
            (1, 2_000_000_001): '0.00000005%',
        }
        for (a, b), expected in cases.items():
            self.assertEqual(
                (f'{a} / {b}', to_pc(a / b)), (f'{a} / {b}', expected)
            )

    def test_n_glyphs(self):
        for s in ('é', 'q̣̇'):
            d = normalize('NFC', s)
            c = normalize('NFD', s)
            self.assertEqual(n_glyphs(c), 1)  # natch
            self.assertEqual(n_glyphs(d), 1)  # less natch

        smiley = chr(0x1F600)
        okA = '\U0001f44c'
        okB = '\U0001f44c\U0001f3fb'
        okC = '\U0001f44c\U0001f3fc'
        okD = '\U0001f44c\N{EMOJI MODIFIER FITZPATRICK TYPE-4}'
        okE = '\U0001f44c\U0001f3fe'
        okF = '\U0001f44c\U0001f3ff'

        mmh = (
            '👨'
            + chr(0x1F3FB)
            + chr(0x200D)
            + '🤝'
            + chr(0x200D)
            + '👨'
            + chr(0x1F3FF)
        )
        mmh2 = '\U0001f468\U0001f3fb\u200d\U0001f91d\u200d\U0001f468\U0001f3ff'

        thumbsup = '\U0001f44d\ufe0f'
        bwthumbsup = '\U0001f44d\ufe0e'
        glyphs = (
            smiley,
            okA,
            okB,
            okC,
            okD,
            okE,
            okF,
            mmh,
            mmh2,
            thumbsup,
            bwthumbsup,
        )
        actual = (
            '\n'.join(
                (f"""('{c}', {len(c)}, {n_glyphs(c)})""") for c in glyphs
            )
            + '\n'
        )
        self.assertStringCorrect(actual, os.path.join(TESTDIR, 'emoji.txt'))

    def test_handle_tilde_non_strings(self):
        self.assertIsNone(handle_tilde(None))
        self.assertEqual(handle_tilde(0), 0)

    def test_handle_tilde_strings(self):
        homedir = os.path.expanduser('~')
        user = os.path.split(homedir)[-1]

        self.assertEqual(
            handle_tilde('~/foo.csv'), os.path.join(homedir, 'foo.csv')
        )
        self.assertEqual(
            handle_tilde('~%s/foo.csv' % user),
            os.path.join(homedir, 'foo.csv'),
        )

        self.assertEqual(
            handle_tilde('~/bar/foo.csv'),
            os.path.join(homedir, 'bar', 'foo.csv'),
        )
        self.assertEqual(
            handle_tilde('~%s/bar/foo.csv' % user),
            os.path.join(homedir, 'bar', 'foo.csv'),
        )

    def test_handle_tilde_non_tilde_trings(self):
        self.assertEqual(handle_tilde('foo.csv'), 'foo.csv')
        self.assertEqual(handle_tilde('/foo.csv'), '/foo.csv')


class TestXMLGeneration(ReferenceTestCase):
    def testSimpleXMLGen(self):
        x = XML()
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, thrέé',
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, thrέé</bar>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testSimpleLatin1XMLGen(self):
        x = XML(inputEncoding='latin1')
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, threé'.encode('latin1'),
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé</bar>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testSimpleLatin9XMLGen(self):
        x = XML(inputEncoding='latin9')
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, threé at €3.'.encode('latin9'),
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé at €3.</bar>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testHarderLatin9XMLGen(self):
        x = XML(inputEncoding='latin9')
        x.OpenElement('foo')
        x.WriteElement(
            'bar',
            'Contents of bar oné, twø, threé at €3.',
            attributes=(('a1', 1), ('a2', 2)),
        )
        x.WriteElement(
            'bas',
            'N/A/N/A of 78042 on N/A at N/Abarceló hotels & resorts'.encode(
                'latin9'
            ),
        )
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(
            stripped,
            """
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé at €3.</bar>
    <bas>N/A/N/A of 78042 on N/A at N/Abarceló hotels &amp; resorts</bas>
</foo>
""".strip(),
        )
        self.assertEqual(type(stripped), str)

    def testHTML5ExternalCSS(self):
        x = XML(html=5, title='Test Page', css=['style.css', 'theme.css'])
        x.WriteElement('h1', 'Hello World')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-ext.html')
        )

    def testHTML5InlineCSS(self):
        x = XML(html=5, title='Test Page', css='body { margin: 0; }')
        x.WriteElement('p', 'Content')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-inline.html')
        )

    def testHTML5EmptyElements(self):
        x = XML(html=5, omitHeader=1)
        x.OpenElement('div', '', {})
        # Non-void empty elements should use open/close tags
        x.WriteElement('td', '', {})
        x.WriteElement('span', '', {})
        x.WriteElement('div', '', {})
        # Void elements should self-close
        x.WriteElement('input', '', {'type': 'text'})
        x.WriteElement('br', '', {})
        x.WriteElement('hr', '', {})
        x.WriteElement('img', '', {'src': 'test.png'})
        x.CloseElement('div')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-empty-elements.html')
        )

    def testHTML5TableFormatting(self):
        x = XML(html=5, omitHeader=1)
        x.OpenElement('table')
        x.OpenElement('tr')
        # Pattern that causes missing newline: OpenElement + CloseElement with tight=True
        x.OpenElement('td')
        x.WriteContent('Cell 1')
        x.CloseElement('td', tight=True)  # This causes missing newline!
        x.WriteElement('td', 'Cell 2')
        x.WriteElement('td', '')  # Empty cell
        x.CloseElement('tr')
        x.CloseElement('table')
        x.CloseXML()
        self.assertStringCorrect(
            x.xml(), os.path.join(TESTDIR, 'html5-table-formatting.html')
        )

    def testSQuote(self):
        self.assertEqual(squote(''), "''")
        self.assertEqual(squote("''"), r"""'\'\''""")
        self.assertEqual(squote("It's"), r"'It\'s'")
        self.assertEqual(
            squote("It's\na\ndog's\nlife."), r"'It\'s\na\ndog\'s\nlife.'"
        )

    def testDQuote(self):
        self.assertEqual(DQuote(''), '""')
        self.assertEqual(DQuote('""'), r'''"\"\""''')
        self.assertEqual(
            DQuote('"So,", she said.\n"So, So"'),
            r'"\"So,\", she said.\n\"So, So\""',
        )

    def testBastardQuoting(self):
        u = r'\!\"\#\$\%\&\'\('
        urepr = repr(u)
        udq = r'''"\\!\\\"\\#\\$\\%\\&\\'\\("'''
        self.assertEqual(u, r'\!\"\#\$\%\&\'\(')  # I know...

        self.assertEqual(repr(u), urepr)  # Again, I know

        self.assertEqual(DQuote(u), udq)
        self.assertEqual(DQuote(u, '"'), udq)

    def testtddadir(self):
        self.assertEqual(tddadir('constraints'), CONSTRAINTSDIR)
        self.assertEqual(tddadir('constraints', 'pd'), PDCONSTRAINTSDIR)

    def testDummy(self):
        d = Dummy(a=1, b=2)
        self.assertEqual(d.a, 1)
        self.assertEqual(d.b, 2)
        self.assertEqual(d.to_dict(), {'a': 1, 'b': 2})

    def testSwapExt(self):
        self.assertEqual(swap_ext('foo.one', '.two'), 'foo.two')
        self.assertEqual(swap_ext('foo.one', 'two'), 'foo.two')
        self.assertEqual(swap_ext('foo', '.two'), 'foo.two')
        self.assertEqual(swap_ext('foo', 'two'), 'foo.two')
        self.assertEqual(swap_ext('foo.one', ''), 'foo')
        self.assertEqual(swap_ext('foo', '.'), 'foo.')

        self.assertEqual(swap_ext('foo', '.txt'), 'foo.txt')
        self.assertEqual(swap_ext('foo', 'txt'), 'foo.txt')
        self.assertEqual(swap_ext('foo.', 'txt'), 'foo.txt')

        self.assertEqual(swap_ext('foo.b', ''), 'foo')

        self.assertEqual(swap_ext('/bar/baz/foo', '.txt'), '/bar/baz/foo.txt')
        self.assertEqual(swap_ext('baz/foo', 'txt'), 'baz/foo.txt')
        self.assertEqual(swap_ext('~/baz/foo.', 'txt'), '~/baz/foo.txt')

        self.assertEqual(swap_ext('a.b.c.d', 'e'), 'a.b.c.e')
        self.assertEqual(swap_ext('a.b.c.d', '.e'), 'a.b.c.e')
        self.assertEqual(swap_ext('/one/two/a.b.c.d', ''), '/one/two/a.b.c')

        self.assertEqual(swap_ext_q('foo.bar', 'bar'), ('foo.bar', False))
        self.assertEqual(swap_ext_q('foo.bar', 'baz'), ('foo.baz', True))

    def testDictToJSON(self):
        refpath = os.path.join(TESTDIR, 'd1.json')
        self.assertStringCorrect(
            dict_to_json({'a': 1, 'b': [1, 2], 'c': {'a': 1}}), refpath
        )
        path = os.path.join(TMPDIR, 'd1.json')
        dict_to_json({'a': 1, 'b': [1, 2], 'c': {'a': 1}}, path)
        self.assertFileCorrect(path, refpath)

    def testDictToTOML(self):
        refpath = os.path.join(TESTDIR, 'd1.toml')
        self.assertStringCorrect(
            dict_to_toml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}), refpath
        )
        path = os.path.join(TMPDIR, 'd1.toml')
        dict_to_toml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}, path)
        self.assertFileCorrect(path, refpath)

    def testDictToYAML(self):
        refpath = os.path.join(TESTDIR, 'd1.yaml')
        self.assertStringCorrect(
            dict_to_yaml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}), refpath
        )
        path = os.path.join(TMPDIR, 'd1.yaml')
        dict_to_yaml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}, path)
        self.assertFileCorrect(path, refpath)

    def test_json_sanitize(self):
        jsd = Dummy(
            Null=None,
            One=1,
            true=True,
            PointFive=0.5,
            String='string',
            List=[1, 2, 3],
            Dict={'a': 1},
            Object=Dummy(foo='bar'),
            Datetime=datetime.datetime(1970, 1, 1, 23, 59, 59),
            Midnight=datetime.datetime(1999, 12, 31, 0, 0, 0),
            Date=datetime.date(1999, 12, 31),
            npnan=np.nan,
            pynan=float('nan'),
        )
        refpath = os.path.join(TESTDIR, 'jsd.json')
        self.assertStringCorrect(dict_to_json(json_sanitize(jsd)), refpath)

    def test_normal_form_tk(self):
        en_dash = unicodedata.lookup('EN DASH')
        em_dash = unicodedata.lookup('EM DASH')
        minus_sign = unicodedata.lookup('MINUS SIGN')

        left_single_quotation_mark = unicodedata.lookup(
            'LEFT SINGLE QUOTATION MARK'
        )
        right_single_quotation_mark = unicodedata.lookup(
            'RIGHT SINGLE QUOTATION MARK'
        )
        modifier_letter_apostrophe = unicodedata.lookup(
            'MODIFIER LETTER APOSTROPHE'
        )
        grave_accent = unicodedata.lookup('GRAVE ACCENT')

        fullwidth_quotation_mark = unicodedata.lookup(
            'FULLWIDTH QUOTATION MARK'
        )
        left_double_quotation_mark = unicodedata.lookup(
            'LEFT DOUBLE QUOTATION MARK'
        )
        right_double_quotation_MARK = unicodedata.lookup(
            'RIGHT DOUBLE QUOTATION MARK'
        )

        no_break_space = unicodedata.lookup('NO-BREAK SPACE')
        en_space = unicodedata.lookup('EN SPACE')
        em_space = unicodedata.lookup('EM SPACE')
        figure_space = unicodedata.lookup('FIGURE SPACE')
        punctuation_space = unicodedata.lookup('PUNCTUATION SPACE')

        tab = '\u00b9'
        superscript_one = unicodedata.lookup('SUPERSCRIPT ONE')
        subscript_one = unicodedata.lookup('SUBSCRIPT ONE')
        circled_digit_one = unicodedata.lookup('CIRCLED DIGIT one')
        mathematical_double_struck_digit_one = unicodedata.lookup(
            'MATHEMATICAL DOUBLE-STRUCK DIGIT ONE'
        )
        parenthesized_digit_one = unicodedata.lookup('PARENTHESIZED DIGIT ONE')
        digit_one_full_stop = unicodedata.lookup('DIGIT ONE FULL STOP')

        greek_capital_letter_alpha = unicodedata.lookup(
            'GREEK CAPITAL LETTER ALPHA'
        )
        latin_capital_letter_a_with_ring_above = unicodedata.lookup(
            'LATIN CAPITAL LETTER A WITH RING ABOVE'
        )
        angstrom_sign = unicodedata.lookup('ANGSTROM SIGN')

        horizontal_ellipsis = unicodedata.lookup('HORIZONTAL ELLIPSIS')
        vertical_ellipsis = unicodedata.lookup('VERTICAL ELLIPSIS')

        midline_horizontal_ellipsis = unicodedata.lookup(
            'MIDLINE HORIZONTAL ELLIPSIS'
        )
        down_right_diagonal_ellipsis = unicodedata.lookup(
            'DOWN RIGHT DIAGONAL ELLIPSIS'
        )

        mapping = {
            en_dash: '-',
            em_dash: '-',
            minus_sign: '-',
            left_single_quotation_mark: "'",
            right_single_quotation_mark: "'",
            modifier_letter_apostrophe: "'",
            grave_accent: "'",
            fullwidth_quotation_mark: '"',
            left_double_quotation_mark: '"',
            right_double_quotation_MARK: '"',
            no_break_space: ' ',
            en_space: ' ',
            em_space: ' ',
            figure_space: ' ',
            punctuation_space: ' ',
            tab: ' ',
            superscript_one: '1',
            subscript_one: '1',
            circled_digit_one: '1',
            mathematical_double_struck_digit_one: '1',
            parenthesized_digit_one: '(1)',
            digit_one_full_stop: '1.',
            greek_capital_letter_alpha: 'A',
            latin_capital_letter_a_with_ring_above: 'A',
            angstrom_sign: 'A',
            horizontal_ellipsis: '...',
            midline_horizontal_ellipsis: '...',
            down_right_diagonal_ellipsis: '...',
            vertical_ellipsis: '...',
            unicodedata.lookup('LATIN SMALL LIGATURE FF'): 'ff',
            unicodedata.lookup('LATIN SMALL LIGATURE FI'): 'fi',
            unicodedata.lookup('LATIN SMALL LIGATURE FL'): 'fl',
            unicodedata.lookup('LATIN SMALL LIGATURE FFI'): 'ffi',
            unicodedata.lookup('LATIN SMALL LIGATURE FFL'): 'ffl',
            unicodedata.lookup('LATIN SMALL LIGATURE ST'): 'st',
            unicodedata.lookup('LATIN SMALL LIGATURE IJ'): 'ij',
        }
        for raw, expected in mapping.items():
            self.assertEqual(
                (raw, normal_form_tk(raw, strip=False)), (raw, expected)
            )
            if expected != ' ':
                self.assertEqual(
                    (raw, normal_form_tk(raw, strip=True)), (raw, expected)
                )

        self.assertEqual(
            normal_form_tk(
                '  The — em-dash  – and en-dash - and  '
                '“various” ‘quotes’ etc … ⋮ ⋯ ⋱  ',
                strip=True,
                standardize_space=True,
            ),
            '''The - em-dash - and en-dash - and "various"'''
            """ 'quotes' etc ... ... ... ...""",
        )

        accents = {
            'àáâäǎæãåā': 'aaaaaaeaaa',
            'ÀÁÂÄǍÆÃÅĀ': 'AAAAAAEAAA',
            'èéêëěẽēėęę': 'eeeeeeeeee',
            'ÈÉÊËĚẼĒĖĘĘ': 'EEEEEEEEEE',
            'ìíîïǐĩīıį': 'iiiiiiiii',
            'ÌÍÎÏǏĨĪİĮ': 'IIIIIIIII',
            'òóôöǒœøõō': 'ooooooeooo',
            'ÒÓÔÖǑŒØÕŌ': 'OOOOOOEOOO',
            'ùúûüǔũūűů': 'uuuuuuuuu',
            'ÙÚÛÜǓŨŪŰŮ': 'UUUUUUUUU',
            'çćčċ ďð ğġ ħ ķ łļľ ñńņň ř ßşșśš țť ŵ ýŷÿ źžż': 'cccc dd gg h k lll nnnn r ssssss tt w yyy zzz',
            'ÇĆČĊ Ď ĞĠ Ķ ĻĽ ÑŃŅŇ Ř ŚŠŞȘ ȚŤ Ŵ ÝŶŸ ŹŽŻ ': 'CCCC D GG K LL NNNN R SSSS TT W YYY ZZZ',
            'ﬀ ﬁ ﬂ ﬃ ﬄ ﬆ œ ӕ Œ Ӕ ĳ': 'ff fi fl ffi ffl st oe ae OE AE ij',
        }
        for k, v in accents.items():
            self.assertEqual(
                (k, normal_form_tk(k, standardize_space=True, strip=True)),
                (k, v),
            )

    def testIsSequence(self):
        self.assertTrue(is_sequence([0, 1]))
        self.assertTrue(is_sequence((0, 1)))
        self.assertTrue(is_sequence(range(2)))
        self.assertTrue(is_sequence(i for i in range(2)))
        self.assertFalse(is_sequence('ab'))

        # Less clear whether these should be, but they are iterable
        self.assertTrue(is_sequence({'a': 1, 'b': 2}))
        self.assertTrue(is_sequence({1, 2}))

    def testListify(self):
        self.assertEqual(listify(None), [])
        self.assertEqual(listify(1), [1])
        self.assertEqual(listify('a'), ['a'])
        self.assertEqual(listify([1]), [1])
        self.assertEqual(listify([]), [])
        self.assertEqual(listify((1,)), [1])
        self.assertEqual(type(listify((1,))), list)
        self.assertEqual(listify(()), [])
        self.assertEqual(type(listify(())), list)

        self.assertEqual(listify({'foo': 1}), [{'foo': 1}])

    def testGloblikeMatch(self):
        names = [f'a{i}' for i in range(21)]
        self.assertEqual(globlike_match(None, names), [])
        self.assertEqual(globlike_match('*', names), names)
        self.assertEqual(globlike_match(['*'], names), names)
        self.assertEqual(globlike_match('a2?', names), ['a20'])
        self.assertEqual(globlike_match('a*2*', names), ['a2', 'a12', 'a20'])
        self.assertEqual(
            globlike_match(['a*2*', 'a10'], names), ['a2', 'a10', 'a12', 'a20']
        )
        self.assertEqual(globlike_match(['a1[23]'], names), ['a12', 'a13'])

    def testTeXName(self):
        cases = {
            'a': 'a',
            'Z': 'Z',
            'a-b': 'aB',
            'A-B': 'AB',
            '_ab': 'Ab',
            '--ab': 'Ab',
            '_-_ab': 'Ab',
            '-_-ab': 'Ab',
            'a1': 'aOne',
            'B2': 'BTwo',
            'x12345678910': 'xOneTwoThreeFourFiveSixSevenEightNineTen',
            'the_big_out10': 'theBigOutTen',
            'The-Kebab-Shak20': 'TheKebabShakTwenty',
            'ab102030405060708090100': 'abTenTwentyThirtyFortyFiftySixtySeventyEightyNinetyOneHundred',
            'from_low_-1000_to_high_20000': 'fromLowOnekToHighTwoxk',
            # These aren't great
            '': 'v',
            '_': 'v',
            '-': 'v',
        }
        for k, v in cases.items():
            self.assertEqual((k, tex_name(k)), (k, v))


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=True)
