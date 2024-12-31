from tdda.referencetest.referencetestcase import ReferenceTestCase, tag
from tdda.utils import *
from unicodedata import normalize

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
    for c in (smiley,
              okA, okB, okC, okD, okE, okF,
              mmh, mmh2,
              thumbsup, bwthumbsup,):
        print(c, len(c), n_glyphs(c))


if __name__ == '__main__':
    ReferenceTestCase.main()
