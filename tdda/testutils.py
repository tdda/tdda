import datetime
import numpy as np
import os
import tempfile

from tdda.referencetest.referencetestcase import ReferenceTestCase, tag
from tdda.utils import (
    to_pc, n_glyphs, handle_tilde, XML, squote, DQuote,
    tddadir, Dummy, swap_ext, dict_to_json, dict_to_toml, dict_to_yaml,
    json_sanitize,
    CONSTRAINTSDIR, PDCONSTRAINTSDIR,
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
            self.assertEqual((f'{a} / {b}', to_pc(a / b)),
                             (f'{a} / {b}', expected))

    def test_n_glyphs(self):
        for s in ('é', 'q̣̇'):
            d = normalize('NFC', s)
            c = normalize('NFD', s)
            self.assertEqual(n_glyphs(c), 1)  # natch
            self.assertEqual(n_glyphs(d), 1)  # less natch

        smiley = chr(0x1F600)
        okA = '\U0001F44C'
        okB = '\U0001F44C\U0001F3FB'
        okC = '\U0001F44C\U0001F3FC'
        okD = '\U0001F44C\N{EMOJI MODIFIER FITZPATRICK TYPE-4}'
        okE = '\U0001F44C\U0001F3FE'
        okF = '\U0001F44C\U0001F3FF'

        mmh = ('👨' + chr(0x1F3FB) + chr(0x200D) + '🤝' + chr(0x200D)
               + '👨' + chr(0x1F3FF))
        mmh2 = '\U0001F468\U0001F3FB\u200D\U0001F91D\u200D\U0001F468\U0001F3FF'


        thumbsup = '\U0001F44D\uFE0F'
        bwthumbsup = '\U0001F44D\uFE0E'
        glyphs = (smiley,
                  okA, okB, okC, okD, okE, okF,
                  mmh, mmh2,
                  thumbsup, bwthumbsup,
        )
        actual = '\n'.join((f'''('{c}', {len(c)}, {n_glyphs(c)})''')
                           for c in glyphs) + '\n'
        self.assertStringCorrect(actual, os.path.join(TESTDIR, 'emoji.txt'))

    def test_handle_tilde_non_strings(self):
        self.assertIsNone(handle_tilde(None))
        self.assertEqual(handle_tilde(0), 0)


    def test_handle_tilde_strings(self):
        homedir = os.path.expanduser('~')
        user = os.path.split(homedir)[-1]

        self.assertEqual(handle_tilde('~/foo.csv'),
                         os.path.join(homedir, 'foo.csv'))
        self.assertEqual(handle_tilde('~%s/foo.csv' % user),
                         os.path.join(homedir, 'foo.csv'))

        self.assertEqual(handle_tilde('~/bar/foo.csv'),
                         os.path.join(homedir, 'bar', 'foo.csv'))
        self.assertEqual(handle_tilde('~%s/bar/foo.csv' % user),
                         os.path.join(homedir, 'bar', 'foo.csv'))

    def test_handle_tilde_non_tilde_trings(self):

        self.assertEqual(handle_tilde('foo.csv'), 'foo.csv')
        self.assertEqual(handle_tilde('/foo.csv'), '/foo.csv')


class TestXMLGeneration(ReferenceTestCase):
    def testSimpleXMLGen(self):
        x = XML()
        x.OpenElement('foo')
        x.WriteElement('bar', 'Contents of bar oné, twø, thrέé',
                       attributes=(('a1', 1), ('a2', 2)))
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(stripped, '''
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, thrέé</bar>
</foo>
'''.strip())
        self.assertEqual(type(stripped), str)

    def testSimpleLatin1XMLGen(self):
        x = XML(inputEncoding='latin1')
        x.OpenElement('foo')
        x.WriteElement('bar', u'Contents of bar oné, twø, threé'.encode('latin1'),
                       attributes=(('a1', 1), ('a2', 2)))
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(stripped, '''
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé</bar>
</foo>
'''.strip())
        self.assertEqual(type(stripped), str)

    def testSimpleLatin9XMLGen(self):
        x = XML(inputEncoding='latin9')
        x.OpenElement('foo')
        x.WriteElement('bar', u'Contents of bar oné, twø, threé at €3.'.encode('latin9'),
                       attributes=(('a1', 1), ('a2', 2)))
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(stripped, '''
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé at €3.</bar>
</foo>
'''.strip())
        self.assertEqual(type(stripped), str)

    def testHarderLatin9XMLGen(self):
        x = XML(inputEncoding='latin9')
        x.OpenElement('foo')
        x.WriteElement('bar', u'Contents of bar oné, twø, threé at €3.',
                       attributes=(('a1', 1), ('a2', 2)))
        x.WriteElement('bas', u'N/A/N/A of 78042 on N/A at N/Abarceló hotels & resorts'.encode('latin9'))
        x.CloseElement()
        stripped = x.xml().strip()
        self.assertEqual(stripped, '''
<?xml version="1.0" encoding="UTF-8"?>
<foo>
    <bar a1="1" a2="2">Contents of bar oné, twø, threé at €3.</bar>
    <bas>N/A/N/A of 78042 on N/A at N/Abarceló hotels &amp; resorts</bas>
</foo>
'''.strip())
        self.assertEqual(type(stripped), str)

    def testSQuote(self):
        self.assertEqual(squote(''), "''")
        self.assertEqual(squote("''"), r"""'\'\''""")
        self.assertEqual(squote("It's"), r"'It\'s'")
        self.assertEqual(squote("It's\na\ndog's\nlife."),
                                r"'It\'s\na\ndog\'s\nlife.'")

    def testDQuote(self):
        self.assertEqual(DQuote(""), '""')
        self.assertEqual(DQuote('""'), r'''"\"\""''')
        self.assertEqual(DQuote('"So,", she said.\n"So, So"'),
                                r'"\"So,\", she said.\n\"So, So\""')

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

    def testDictToJSON(self):
        refpath = os.path.join(TESTDIR, 'd1.json')
        self.assertStringCorrect(
            dict_to_json({'a': 1, 'b': [1, 2], 'c': {'a': 1}}),
            refpath
        )
        path = os.path.join(TMPDIR, 'd1.json')
        dict_to_json({'a': 1, 'b': [1, 2], 'c': {'a': 1}}, path)
        self.assertFileCorrect(path, refpath)

    def testDictToTOML(self):
        refpath = os.path.join(TESTDIR, 'd1.toml')
        self.assertStringCorrect(
            dict_to_toml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}),
            refpath
        )
        path = os.path.join(TMPDIR, 'd1.toml')
        dict_to_toml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}, path)
        self.assertFileCorrect(path, refpath)

    def testDictToYAML(self):
        refpath = os.path.join(TESTDIR, 'd1.yaml')
        self.assertStringCorrect(
            dict_to_yaml({'a': 1, 'b': [1, 2], 'c': {'a': 1}}),
            refpath
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
            Datetime=datetime.datetime(1970,1,1,23,59,59),
            Midnight=datetime.datetime(1999,12,31,0,0,0),
            Date=datetime.date(1999,12,31),
            npnan=np.nan,
            pynan=float('nan')
        )
        refpath = os.path.join(TESTDIR, 'jsd.json')
        self.assertStringCorrect(dict_to_json(json_sanitize(jsd)), refpath)

if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=True)
