# -*- coding: utf-8 -*-

"""
URLs1

 http\:\/\/[a-z]{3,4}\.[a-z]{3,4}
 http\:\/\/[a-z]{5,19}\.com\/
 [a-z]{4,5}\:\/\/[a-z]{3}\.[a-z]{6,19}\.com
 http\:\/\/www\.[a-z]{6,19}\.com\/
 http\:\/\/www\.[a-z]{6,19}\.co\.uk\/

** With s replacing space and backslashes removed, spaced in groups:

 111111111   222  33333333333  4  5555555555   6  777  8  99  10
 http        ://  [a-z]{3,4}   .  [a-z]{3,4}
 http        ://  [a-z]{5,19}  .  com          /
 [a-z]{4,5}  ://  [a-z]{3}     .  [a-z]{6,19}  .  com
 http        ://  www          .  [a-z]{6,19}  .  com  /
 http        ://  www          .  [a-z]{6,19}  .  co   .  uk  /

--> :// is very special in col 2

 111111111   222  33333333333  4  5555555555   6  777  8  99  10
 http        ://  [a-z]{3,4}   .  [a-z]{3,4}
 http        ://  [a-z]{5,19}  .  com          /
 [a-z]{4,5}  ://  [a-z]{3}     .  [a-z]{6,19}  .  com
 http        ://  www          .  [a-z]{6,19}  .  com  /
 http        ://  www          .  [a-z]{6,19}  .  co   .  uk  /

--> /, when present is always last in RH group

 111111111   222  33333333333  4  5555555555   6  777  8  99  10
 http        ://  [a-z]{3,4}   .  [a-z]{3,4}
 http        ://  [a-z]{5,19}  .  com                         /
 [a-z]{4,5}  ://  [a-z]{3}     .  [a-z]{6,19}  .  com
 http        ://  www          .  [a-z]{6,19}  .  com         /
 http        ://  www          .  [a-z]{6,19}  .  co   .  uk  /



Goal:

 111111111   222  33333333333  4  5555555555   6  777  8  99  10
 http        ://  [a-z]{3,4}   .  [a-z]{3,4}
 http        ://  [a-z]{5,19}  .  com                         /
 [a-z]{4,5}  ://  [a-z]{3}     .  [a-z]{6,19}  .  com
 http        ://  www          .  [a-z]{6,19}  .  com         /
 http        ://  www          .  [a-z]{6,19}  .  co   .  uk  /

URLs 1 + 2:

 [a-z]{3,4}\.[a-z]{2,4}
 [a-z]{5,19}\.com\/
 [a-z]{3,4}[\.\/\:]{1,3}[a-z]{3,19}\.[a-z]{3,4}
 http\:\/\/[a-z]{5,19}\.com\/
 [a-z]{4,5}\:\/\/[a-z]{3}\.[a-z]{6,19}\.com
 http\:\/\/www\.[a-z]{6,19}\.com\/
 http\:\/\/www\.[a-z]{6,19}\.co\.uk\/

** With s replacing space and backslashes removed, spaced in groups:

 11111111111  2222222222  33333333333  4  55555555555  6  777  8  99  10
 [a-z]{3,4}   .           [a-z]{2,4}
 [a-z]{5,19}  .           com          /
 [a-z]{3,4}   [./:]{1,3}  [a-z]{3,19}  .  [a-z]{3,4}
 http         ://         [a-z]{5,19}  .  com          /
 [a-z]{4,5}   ://         [a-z]{3}     .  [a-z]{6,19}  .  com
 http         ://         www          .  [a-z]{6,19}  .  com  /
 http         ://         www          .  [a-z]{6,19}  .  co   .  uk  /

Goal:

 11111111111  2222222222  33333333333  4  55555555555  6  777  8  99  10
                          [a-z]{3,4}   .  [a-z]{2,4}
                          [a-z]{5,19}  .  com                         /
 [a-z]{3,4}   [./:]{1,3}  [a-z]{3,19}  .  [a-z]{3,4}
 http         ://         [a-z]{5,19}  .  com                         /
 [a-z]{4,5}   ://         [a-z]{3}     .  [a-z]{6,19}  .  com
 http         ://         www          .  [a-z]{6,19}  .  com         /
 http         ://         www          .  [a-z]{6,19}  .  co   .  uk  /



TELEPHONES 2

 \(\d{3,4}\) \d{3,4} \d{4}
 \+\d{1,2} \d{2,3} \d{3,4} \d{4}

** With s replacing space and backslashes removed, spaced in groups:

 1  2222222  3  4444444  5555555   666666  77777  8888
 (  d{3,4}   )  s        d{3,4}    s       d{4}
 +  d{1,2}   s  d{2,3}   s         d{3,4}  s      d{4}

-->  Space at pos -2

 1  2222222  3  4444444  5555555   666666  77777  8888
 (  d{3,4}   )  s        d{3,4}            s      d{4}
 +  d{1,2}   s  d{2,3}   s         d{3,4}  s      d{4}

-->  Space at pos -2 within left group

 1  2222222  3  4444444  5555555   666666  77777  8888
 (  d{3,4}   )           s         d{3,4}  s      d{4}
 +  d{1,2}   s  d{2,3}   s         d{3,4}  s      d{4}



Goal

 1  2222222  3  4444444  5555555   666666  77777  8  9999
 (  d{3,4}   )  s        d{3,4}    s       d{4}
 +  d{1,2}      s        d{2,3}    s       d{3,4} s  d{4}





TELEPHONES 5

 \d{3} \d{3} \d{4}
 \d{3}\-\d{3}\-\d{4}
 1 \d{3} \d{3} \d{4}
 \(\d{3}\) \d{3} \d{4}

** With s replacing space and backslashes removed, spaced in groups:

 1111  2222  3333  4  5555  6  7777
 d{3}  s     d{3}  s  d{4}
 d{3}  -     d{3}  -  d{4}
 1     s     d{3}  s  d{3}  s  d{4}
 (     d{3}  )     s  d{3}  s  d{4}

--> Last group is always 4 digits

 1111  2222  3333  4  5555  6  7777
 d{3}  s     d{3}  s           d{4}
 d{3}  -     d{3}  -           d{4}
 1     s     d{3}  s  d{3}  s  d{4}
 (     d{3}  )     s  d{3}  s  d{4}

--> Group -2 with left part is always 3 digits

 1111  2222  3333  4  5555  6  7777
 d{3}  s              d{3}  s  d{4}
 d{3}  -              d{3}  -  d{4}
 1     s     d{3}  s  d{3}  s  d{4}
 (     d{3}  )     s  d{3}  s  d{4}

--> Last of left of left is always space or hyphen

 1111  2222  3333  4  5555  6  7777
 d{3}              s  d{3}  s  d{4}
 d{3}              -  d{3}  -  d{4}
 1     s     d{3}  s  d{3}  s  d{4}
 (     d{3}  )     s  d{3}  s  d{4}

--> Within left three, there is always a block of 3 digits

 1  2  3333  4  5  6666  7  8888
       d{3}     s  d{3}  s  d{4}
       d{3}     -  d{3}  -  d{4}
 1  s  d{3}     s  d{3}  s  d{4}
 (     d{3}  )  s  d{3}  s  d{4}


Goal:

 1  2222  3  4444  5  6666  7  8888
             d{3}  s  d{3}  s  d{4}
             d{3}  -  d{3}  -  d{4}
    1     s  d{3}  s  d{3}  s  d{4}
 (  d{3}  )        s  d{3}  s  d{4}



TELS 1-5

 \d{3} \d{3} \d{4}
 \d{3,4}[\-\.]\d{3}[\-\.]\d{4}
 1 \d{3} \d{3} \d{4}
 \(\d{3,4}\) \d{3,4} \d{4}
 \+\d{1,2} \d{2,3} \d{3,4} \d{4}


** With s replacing space and backslashes removed, spaced in groups:

 111111  222222  3333  444444  555555  666666  7777  8888
 d{3}    s       d{3}  s       d{4}
 d{3,4}  [-.]    d{3}  [-.]    d{4}
 1       s       d{3}  s       d{3}    s       d{4}
 (       d{3,4}  )     s       d{3,4}  s       d{4}
 +       d{1,2}  s     d{2,3}  s       d{3,4}  s     d{4}


Goal:

 1  222222  3333  444444  555555  6666  777777  8  9999
    d{3}          s       d{3}    s     d{4}
    d{3,4}  [-.]          d{3}    [-.]  d{4}
    1             s       d{3}    s     d{3}    s  d{4}
 (  d{3,4}  )     s       d{3,4}  s     d{4}
 +  d{1,2}        s       d{2,3}  s     d{3,4}  s  d{4}
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import sys
import unittest

from collections import OrderedDict

try:
    import pandas
except:
    pandas = None
pd = pandas

#from artists.miro.writabletestcase import WritableTestCase
from tdda.rexpy.relib import re
from tdda.rexpy import *
from tdda.rexpy.rexpy import Coverage


class TestUtilityFunctions(unittest.TestCase):
    def test_signature(self):
        self.assertEqual(signature([]), '')

        self.assertEqual(signature([('c', 1)]), 'c')

        self.assertEqual(signature([('C', 3), ('.', 1),
                                    ('C', 2), ('.', 1),
                                    ('C', 2)]), 'C.C.C')

        self.assertEqual(signature([('C', 8), ('.', 1),
                                    ('C', 4), ('.', 1),
                                    ('C', 4), ('.', 1),
                                    ('C', 4), ('.', 1),
                                    ('C', 12)]), 'C.C.C.C.C')

        self.assertEqual(signature([('.', 1),
                                    ('C', 4), ('.', 1), (' ', 1),
                                    ('C', 3), (' ', 1),
                                    ('C', 4)]), '.C. C C')

        self.assertEqual(signature([('C', 4), ('.', 1),
                                    ('C', 2), ('.', 1),
                                    ('C', 5), ('.', 1),
                                    ('C', 2), ('.', 1,),
                                    ('C', 2), (' ', 1), ('.', 1),
                                    ('C', 5)]), 'C.C.C.C.C .C')

        self.assertEqual(signature([('C', 4), ('.', 1),
                                    ('C', 2), ('.', 1),
                                    ('C', 5), ('.', 1),
                                    ('C', 2), ('.', 1),
                                    ('C', 2), ('*', 1), ('.', 1),
                                    ('C', 5)]), 'C.C.C.C.C*.C')


    def test_get_omnipresent_at_pos(self):
        c = {
            ('a', 1, 1, 'fixed'): {1: 7, -1: 7, 3: 4},
            ('b', 1, 1, 'fixed'): {2: 6, 3: 4},
            ('c', 1, 1): {3: 1, 4: 2, 2: 7},
            ('d', 1, 1, 'fixed'): {1: 1}
        }

        self.assertEqual(get_omnipresent_at_pos(c, 7),
                         [((u'a', 1, 1, u'fixed'), -1),
                          ((u'a', 1, 1, u'fixed'), 1),
                          ((u'c', 1, 1), 2)])

        self.assertEqual(get_omnipresent_at_pos(c, 6),
                         [((u'b', 1, 1, u'fixed'), 2)])


        self.assertEqual(get_omnipresent_at_pos(c, 5), [])

        self.assertEqual(get_omnipresent_at_pos({}, 1), [])

        self.assertEqual(get_omnipresent_at_pos({}, 0), [])

    def test_length_stats(self):
        # Testing with strings, but works with lists etc. too
        self.assertEqual(length_stats(['abc', 'def', 'ghi']), (True, 3))
        self.assertEqual(length_stats(['a', 'def', 'gh']), (False, 3))
        self.assertEqual(length_stats([]), (True, 0))

    def test_left_parts1(self):
        # For this test, the fragments are always present in the positions
        p1 = [('a',), ('b',), ('c',), ('d',), ('e',), ('f',)]
        p2 = [('A',), ('b',), ('C',), ('d',), ('E',)]
        p3 = [('.',), ('b',), ('.',), ('d',)]
        fixed = [(('b',), 1), (('d',),  3)]
        expected = [
            [[('a',)],          [('A',)],  [('.',)]],
            [[('b',)],          [('b',)],  [('b',)]],
            [[('c',)],          [('C',)],  [('.',)]],
            [[('d',)],          [('d',)],  [('d',)]],
            [[('e',), ('f',)],  [('E',)],  []]
        ]
        self.assertEqual(left_parts([p1, p2, p3], fixed), expected)

    def test_left_parts2(self):
        # For this test, the fragments are always present in the positions
        p1 = [('a',), ('b',), ('c',), ('d',), ('e',), ('f',)]
        p2 = [('a',), ('B',), ('C',), ('d',), ('E',)]
        p3 = [('a',), ('b',), ('c',), ('d',)]
        fixed = [(('a',), 0), (('c',),  3)]
        expected = [
            [[('a',)],           [('a',)],          [('a',)]],
            [[('b',), ('c',)],   [('B',), ('C',)],  [('b',), ('c',)]],
            [[('d',)],           [('d',)],          [('d',)]],
            [[('e',), ('f',)],   [('E',)],          []]
        ]
        self.assertEqual(left_parts([p1, p2, p3], fixed), expected)

    def test_right_parts1(self):
        p1 = [('F',), ('e',), ('d',), ('c',), ('b',), ('a',)]
        p2 = [('E',), ('d',), ('C',), ('b',), ('A',)]
        p3 = [('d',), ('.',), ('b',), ('.',)]
        fixed = [(('b',), 2), (('d',),  4)]
        expected = [
            [[('F',), ('e',)],  [('E',)],  []],
            [[('d',)],          [('d',)],  [('d',)]],
            [[('c',)],          [('C',)],  [('.',)]],
            [[('b',)],          [('b',)],  [('b',)]],
            [[('a',)],          [('A',)],  [('.',)]],
        ]
        self.assertEqual(right_parts([p1, p2, p3], fixed), expected)

    def test_right_parts2(self):
        p1 = [('F',), ('e',), ('d',), ('c',), ('b',), ('a',)]
        p2 = [('E',), ('d',), ('C',), ('b',), ('a',)]
        p3 = [('d',), ('.',), ('.',), ('a',)]
        fixed = [(('a',), 1), (('d',),  4)]
        expected = [
            [[('F',), ('e',)],  [('E',)],  []],
            [[('d',)],          [('d',)],  [('d',)]],
            [[('c',), ('b',)],  [('C',), ('b',)],  [('.',), ('.',)]],
            [[('a',)],          [('a',)],  [('a',)]],
        ]
        self.assertEqual(right_parts([p1, p2, p3], fixed), expected)

    def test_ndigits(self):
        self.assertEqual(ndigits(1, 1), '1')
        self.assertEqual(ndigits(2, 1), '1' * 2)
        self.assertEqual(ndigits(1, 2), '2')
        self.assertEqual(ndigits(2, 2), '2' * 2)
        self.assertEqual(ndigits(0, 2), '')
        self.assertEqual(ndigits(11, 9), '9' * 11)
        self.assertEqual(ndigits(9, 11), 'B' * 9)
        self.assertEqual(ndigits(9, 10), 'A' * 9)
        self.assertEqual(ndigits(10,9), '9' * 10)
        self.assertEqual(ndigits(10,10), 'A' * 10)
        self.assertEqual(ndigits(5,35), 'Z' * 5)
        # Not really designed for more than 35 parts.
        # But if it happens, just carries on
        self.assertEqual(ndigits(5, 36), chr(ord('Z') + 1) * 5)
        # Also not supposed to take digits below 1.
        # but...
        self.assertEqual(ndigits(4, 0), '0' * 4)

    def test_aligned_parts1(self):
        x = Extractor([])
        part1 = [
                    [('a', 1, 1, 'fixed'), ('b', 1, 1, 'fixed')],
                    [('c', 1, 1, 'fixed')],
                ]
        part2 = [
                    [('/', 1, 1, 'fixed')],
                    [('/', 1, 1, 'fixed')],
                ]
        parts = [part1, part2]
        expected = '\n'.join(['|1 2|3|',
                              ' a b /',
                              ' c   /'])
        self.assertEqual(x.aligned_parts(parts), expected)

    def test_aligned_parts2(self):
        x = Extractor([])
        part1 = [
                    [('a', 1, 1, 'fixed'), ('b', 1, 1, 'fixed')],
                    [('c', 1, 1, 'fixed')],
                ]
        part2 = [
                    [],
                    [('/', 1, 1, 'fixed')],
                ]
        part3 = [
                    [('.', 1, 1, 'fixed')],
                    [],
                ]
        part4 = [
                    [('!', 1, 1, 'fixed')],
                    [('!', 1, 1, 'fixed')],
                ]
        parts = [part1, part2, part3, part4]
        expected = '\n'.join(['|1 2|3|4|5|',
                              ' a b   . !',
                              ' c   /   !'])
        self.assertEqual(x.aligned_parts(parts), expected)



class TestHelperMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.x = Extractor([])

    def test_coarse_character_classification(self):
        x = self.x
        for i in range(ord('A'), ord('Z') + 1):
            self.assertEqual(x.coarse_classify_char(chr(i)), C)
        for i in range(ord('a'), ord('z') + 1):
            self.assertEqual(x.coarse_classify_char(chr(i)), C)
        for i in range(ord('0'), ord('9') + 1):
            self.assertEqual(x.coarse_classify_char(chr(i)), C)
        for c in ' \t\r\n\f\v':
            self.assertEqual(x.coarse_classify_char(c), ' ')
        for c in '!"#$%&' + "'" + '()*+,-.' + '\\' + ':;<=>?@[\]^_`{|}~':
            self.assertEqual(x.coarse_classify_char(c), '.')
        for i in range(0, 0x1c):  # 1C to 1F are considered whitespace
                                  # in unicode
            c = chr(i)
            if not c in '\t\r\n\f\v':
                self.assertEqual(x.coarse_classify_char(c), '*')

    def test_coarse_string_classification(self):
        x = self.x
        for i in range(ord('A'), ord('Z') + 1):
            self.assertEqual(x.coarse_classify_char(chr(i)), C)
        for i in range(ord('a'), ord('z') + 1):
            self.assertEqual(x.coarse_classify_char(chr(i)), C)
        for i in range(ord('0'), ord('9') + 1):
            self.assertEqual(x.coarse_classify_char(chr(i)), C)
        for c in ' \t\r\n\f\v':
            self.assertEqual(x.coarse_classify_char(c), ' ')
        for c in ' \t\r\n\f\v':
            self.assertEqual(x.coarse_classify_char(c), ' ')
        for c in '!"#$%&' + "'" + '()*+,-.' + '\\' + ':;<=>?@[\]^_`{|}~':
            self.assertEqual(x.coarse_classify_char(c), '.')
        for i in range(0, 0x1c):  # 1C to 1F are considered whitespace
                                  # in unicode
            c = chr(i)
            if not c in '\t\r\n\f\v':
                self.assertEqual(x.coarse_classify_char(c), '*')
        self.assertEqual(x.coarse_classify_char(chr(127)), '*')

    def test_coarse_classification(self):
        x = self.x
        self.assertEqual(x.coarse_classify('255-SI-32'),
                                         CtoUC('CCC.CC.CC'))
        guid = '1f65c9e8-cf9a-4e53-b7d0-c48a26a21b7c'
        sig  = CtoUC('CCCCCCCC.CCCC.CCCC.CCCC.CCCCCCCCCCCC')
        self.assertEqual(x.coarse_classify(guid), sig)
        self.assertEqual(x.coarse_classify('(0131) 123 4567'),
                                           CtoUC('.CCCC. CCC CCCC'))
        self.assertEqual(x.coarse_classify('2016-01-02T10:11:12 +0300z'),
                                           CtoUC('CCCC.CC.CCCCC.CC.CC .CCCCC'))
        self.assertEqual(x.coarse_classify('2016-01-02T10:11:12\a+0300z'),
                                           CtoUC('CCCC.CC.CCCCC.CC.CC*.CCCCC'))

    def test_run_length_encoding(self):
        self.assertEqual(run_length_encode(''), ())

        self.assertEqual(run_length_encode('c'), (('c', 1),))

        self.assertEqual(run_length_encode('CCC.CC.CC'),
                                           (('C', 3), ('.', 1),
                                            ('C', 2), ('.', 1),
                                            ('C', 2)))

        sig  = 'CCCCCCCC.CCCC.CCCC.CCCC.CCCCCCCCCCCC'
        self.assertEqual(run_length_encode(sig), (('C', 8), ('.', 1),
                                         ('C', 4), ('.', 1),
                                         ('C', 4), ('.', 1),
                                         ('C', 4), ('.', 1),
                                         ('C', 12)))

        self.assertEqual(run_length_encode('.CCCC. CCC CCCC'),
                         (('.', 1),
                          ('C', 4), ('.', 1), (' ', 1),
                          ('C', 3), (' ', 1),
                          ('C', 4)))

        self.assertEqual(run_length_encode('CCCC.CC.CCCCC.CC.CC .CCCCC'),
                         (('C', 4), ('.', 1),
                          ('C', 2), ('.', 1),
                          ('C', 5), ('.', 1),
                          ('C', 2), ('.', 1,),
                          ('C', 2), (' ', 1), ('.', 1),
                          ('C', 5)))

        self.assertEqual(run_length_encode('CCCC.CC.CCCCC.CC.CC*.CCCCC'),
                         (('C', 4), ('.', 1),
                          ('C', 2), ('.', 1),
                          ('C', 5), ('.', 1),
                          ('C', 2), ('.', 1),
                          ('C', 2), ('*', 1), ('.', 1),
                          ('C', 5)))

    def test_cleaning(self):
        examples = ['123-AB-321', ' 123-AB-321', '', None, '321-BA-123 ']
        keys = ['123-AB-321', '321-BA-123']
        x = Extractor(examples, remove_empties=True, strip=True)
        self.assertEqual(set(x.example_freqs.keys()), set(keys))
        self.assertEqual(x.n_stripped, 2)
        self.assertEqual(x.n_empties, 1)
        self.assertEqual(x.n_nulls, 1)
        items = x.example_freqs.keys()
        self.assertEqual(set(items), {'123-AB-321', '321-BA-123'})

    def test_cleaning_keep_empties(self):
        examples = ['123-AB-321', ' 123-AB-321', '', None, '321-BA-123 ']
        keys = ['123-AB-321', '321-BA-123', '']
        x = Extractor(examples, remove_empties=False, strip=True)
        self.assertEqual(set(x.example_freqs.keys()), set(keys))
        self.assertEqual(x.n_stripped, 2)
        self.assertEqual(x.n_empties, 0)
        self.assertEqual(x.n_nulls, 1)
        items = x.example_freqs.keys()
        self.assertEqual(set(items), {'123-AB-321', '321-BA-123', ''})

    def test_cleaning_no_strip_no_empties(self):
        examples = ['123-AB-321', ' 123-AB-321', '', None, '321-BA-123 ']
        keys = ['123-AB-321', '', ' 123-AB-321', '321-BA-123 ']
        x = Extractor(examples, remove_empties=False, strip=False)
        self.assertEqual(set(x.example_freqs.keys()), set(keys))
        self.assertEqual(x.n_stripped, 0)
        self.assertEqual(x.n_empties, 0)
        self.assertEqual(x.n_nulls, 1)
        items = x.example_freqs.keys()
        self.assertEqual(set(items), set(keys))

    def test_batch_rle_extract_single(self):
        examples = ['123-AB-321', '123-AB-321',  None, '321-BA-123']
        x = Extractor(examples)
        freqs = x.results.rle_freqs
        self.assertEqual(len(freqs), 1)
        key = ((C, 3), ('.', 1), (C, 2), ('.', 1), (C, 3))
        self.assertEqual(list(freqs.keys()), [key])
        self.assertEqual(freqs[key], 2)

    def test_batch_rle_extract_pair(self):
        examples = ['123-AB-321', '12-AB-4321', None, '321-BA-123']
        x = Extractor(examples)
        freqs = x.results.rle_freqs
        self.assertEqual(len(freqs), 2)
        key1 = ((C, 3), ('.', 1), (C, 2), ('.', 1), (C, 3))
        key2 = ((C, 2), ('.', 1), (C, 2), ('.', 1), (C, 4))
        keys = [key1, key2]
        self.assertEqual(set(freqs.keys()), set(keys))
        self.assertEqual(freqs[key1], 2)
        self.assertEqual(freqs[key2], 1)

    def test_rle2re(self):
        Cats = self.x.Cats
        rle = (('C', 3), ('.', 1), ('C', 2), ('.', 1), ('C', 3))
        an = Cats.AlphaNumeric.re_string
        punc = Cats.Punctuation.re_string
        regex = self.x.rle2re(rle)
        self.assertEqual(regex,
                         '^%s{3}%s%s{2}%s%s{3}$' % (an, punc, an, punc, an))
        cre = re.compile(regex)
        for s in ['123-AB-321', '321-BA-123']:
            self.assertIsNotNone(re.match(cre, s))

    def test_vrle(self):
        key1 = (('C', 3), ('.', 1), ('C', 2), ('.', 1), ('C', 3))
        key2 = (('C', 2), ('.', 1), ('C', 2), ('.', 1), ('C', 4))
        keys = [key1, key2]
        range_rles = to_vrles(keys)
        self.assertEqual(range_rles, [(('C', 2, 3), ('.', 1, 1),
                                       ('C', 2, 2), ('.', 1, 1),
                                       ('C', 3, 4))])

    def test_vrle2re(self):
        key1 = (('C', 3), ('.', 1), ('C', 2), ('.', 1), ('C', 3))
        key2 = (('C', 2), ('.', 1), ('C', 2), ('.', 1), ('C', 4))
        keys = [key1, key2]
        rrle = [('C', 2, 3), ('.', 1, 1),
                ('C', 2, 2), ('.', 1, 1),
                ('C', 3, 4)]
        Cats = Extractor([]).Cats
        an = Cats.AlphaNumeric.re_string
        punc = Cats.Punctuation.re_string
        expected = '^%s{2,3}%s%s{2}%s%s{3,4}$' % (an, punc, an, punc, an)
        x = Extractor([])
        self.assertEqual(x.vrle2re(rrle), expected)

    def test_sort_by_len(self):
        # Really designed for sorting lists/tuples, but everything with
        # a length will behave the same
        x = Extractor(['a'])
        self.assertEqual(x.sort_by_length([]), [])
        self.assertEqual(x.sort_by_length(['a']), ['a'])
        self.assertEqual(x.sort_by_length(['a', 'ab']), ['a', 'ab'])
        self.assertIn(x.sort_by_length(
                ['abcdef', '', 'aa', 'bb', 'ccc', 'zzyy', '1']),
                (['', '1', 'aa', 'bb', 'ccc', 'zzyy', 'abcdef'],
                 ['', '1', 'bb', 'aa', 'ccc', 'zzyy', 'abcdef']))

    def test_split_left(self):
        x = Extractor(['a'])
        http = [('http', 1, 1, 'fixed'),
                ('://', 1, 1, 'fixed'),
                ('a', 1, 5),
                ('.', 1, 1, 'fixed'),
                ('com', 1, 1, 'fixed')]
        https = [('https', 1, 1, 'fixed'),
                 ('://', 1, 1, 'fixed'),
                 ('a', 1, 4),
                 ('#', 1, 1, 'fixed'),
                 ('co', 1, 1, 'fixed'),
                 ('.', 1, 1, 'fixed'),
                 ('uk', 1, 1, 'fixed'),
                 ('/', 1, 1, 'fixed')]
        patterns = [http, https]
        results = x.merge_fixed_omnipresent_at_pos(patterns)
        expected = [
                [
                    [(u'http', 1, 1, u'fixed')],
                    [(u'https', 1, 1, u'fixed')]
                ],

                [
                    [(u'://', 1, 1, u'fixed')],
                    [(u'://', 1, 1, u'fixed')],
                ],

                [
                    [(u'a', 1, 5),
                     (u'.', 1, 1, u'fixed'),
                     (u'com', 1, 1, u'fixed')],

                    [(u'a', 1, 4),
                     (u'#', 1, 1, u'fixed'),
                     (u'co', 1, 1, u'fixed'),
                     (u'.', 1, 1, u'fixed'),
                     (u'uk', 1, 1, u'fixed'),
                     (u'/', 1, 1, u'fixed')]
                ],
        ]
        self.assertEqual(results, expected)


class TestExtraction(unittest.TestCase):

    def check_result(self, result, rexes, examples):
        self.assertEqual(result, rexes)
        compiled = [re.compile(r) for r in rexes]
        self.assertEqual(all(any(re.match(rex, x) for rex in compiled)
                             for x in examples if x),
                         True)

    def test_re_pqs_id(self):
        # Space in second string should cause \s* at start, no?
        iids = ['123-AB-321', ' 12-AB-4321', '', None, '321-BA-123 ']
        rexes = [r'^\s*\d{2,3}\-[A-Z]{2}\-\d{3,4}\s*$']
        x = extract(iids, strip=True, remove_empties=True)
        self.check_result(x, rexes, iids)

    def test_re_pqs_id_with_dash(self):
        iids = ['123-AB-321', '12-AB-4321', '', None, '321-BA-123']
        rexes = [r'^$', r'^\d{2,3}[A-Z\-][A-Z]{2}[A-Z\-]\d{3,4}$']
        x = extract(iids, extra_letters='-')
        self.check_result(x, rexes, iids)
        # Test result has changed with improved behaviour.
        # Now us spots that the base sequence is the same
        # Previously this found this:
        #        [r'^\s*[A-Z0-9\-]{10}\s*$'])

    def test_re_pqs_id_with_dash2(self):
        iids = ['123-AB-321', 'AB-1B-4A21', None, '321-BA-1A23']
        rexes = [r'^[A-Z0-9\-]{10,11}$']
        x = extract(iids, extra_letters='-')
        self.check_result(x, rexes, iids)

    def test_re_pqs_id_with_underscore(self):
        iids = ['123_AB_321', 'AB_1B_4A21', None, '321_BA_1A23ab2rj']
        rexes = [r'^[A-Za-z0-9\_]+$']
        x = extract(iids, extra_letters='_')
        self.check_result(x, rexes, iids)

    def test_re_pqs_id_with_underscores2(self):
        iids = ['123_AB_321', 'AB_1B_4A21', None, '321_BA_1A23ab2rj']
        rexes = [r'^[A-Za-z0-9\_]+$']
        x = extract(iids, extra_letters='_-')
        self.check_result(x, rexes, iids)

    def test_re_pqs_id_with_underscores3(self):
        iids = ['123-AB_321', 'AB_1B-4A21', None, '321_BA_1A23ab2rj']
        rexes = [r'^[A-Za-z0-9\_\-]+$']
        x = extract(iids, extra_letters='_-.')
        self.check_result(x, rexes, iids)

    def test_re_uuid(self):
        uuids = ['1f65c9e8-cf9a-4e53-b7d0-c48a26a21b7c',
                 '88888888-4444-4444-4444-cccccccccccc',
                 'aaaaaaaa-1111-0000-9999-0123456789ab',
                 '22ecc913-68eb-4cfb-a9cc-18df44137a4c',
                 '634962c3-8bc1-4b51-b36d-3dcbfdc92b63',
                 'aac65b99-92ff-11e6-b97d-b8f6b118f191',
                 '6fa459ea-ee8a-3ca4-8f4e-db77e160355e',
                 '886313e1-3b8a-e372-9b90-0c9aee199e5d']
        rexes = ['^[0-9a-f]{8}\\-[0-9a-f]{4}\\-[0-9a-f]{4}\\-'
                 '[0-9a-f]{4}\\-[0-9a-f]{12}$']
        x = extract(uuids)
        self.check_result(x, rexes, uuids)

    def test_re_uuid4(self):
        uuid4s = ['2ffb8eaa-dd75-41c2-aca6-0444914b8713',
                  'f69c5651-0b97-4909-b896-8ef0891f81ff',
                  '13f984fe-65db-4646-99d4-a93c06f78472',
                  '50a886d2-78c9-4b7b-81a9-25caf4deb212',
                  '2d4429df-9a80-b581-9565-27880ce171b0',
                  '857e0ec6-1511-478b-93a3-15ac9212fd0d']

        rexes = [r'^[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-'
                 r'[0-9a-f]{4}\-[0-9a-f]{12}$']

        x = extract(uuid4s, variableLengthFrags=True)       # Not refining down yet
        self.check_result(x, rexes, uuid4s)

    tels1 = [
        '(0131) 496 0091',
        '(0131) 496 0161',
        '(0131) 496 0107',
        '(020) 7946 0106',
        '(020) 7946 0642',
        '(0141) 496 0927',
        '(0141) 496 0595',
        '(0141) 496 0236',
        '(0141) 496 0324'
    ]
    def test_tels1(self):
        x = extract(self.tels1)
        self.check_result(x, [r'^\(\d{3,4}\) \d{3,4} \d{4}$'], self.tels1)


    tels2 = [
        '+44 131 496 0091',
        '(0131) 496 0161',
        '+44 131 496 0107',
        '(020) 7946 0106',
        '+44 20 7946 0642',
        '+44 141 496 0927',
        '(0141) 496 0595',
        '+1 202 555 0181',
        '(0141) 496 0324',
    ]
    def test_tels2(self):
        x = set(extract(self.tels2))
        rexes = set([r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$',
                     r'^\(\d{3,4}\) \d{3,4} \d{4}$'])
        self.check_result(x, rexes, self.tels2)

    def test_coverage_tels2(self):
        x = Extractor(self.tels2)
        rex = x.results.rex
        d = dict(zip(rex, x.coverage()))
        self.assertEqual(d,
                         {
                            r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$': 5,
                            r'^\(\d{3,4}\) \d{3,4} \d{4}$': 4,
                         })
        expected = set([r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$',
                        r'^\(\d{3,4}\) \d{3,4} \d{4}$'])
        self.check_result(set(rex), expected, self.tels2)

    def test_incremental_coverage_tels2(self):
        x = Extractor(self.tels2)
        rex = x.results.rex
        od = x.incremental_coverage()
        self.assertEqual(od,
                         OrderedDict((
                            (r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$', 5),
                            (r'^\(\d{3,4}\) \d{3,4} \d{4}$', 4),
                         )))

    def test_coverage_tels2_dedup(self):
        x = Extractor(self.tels2 + self.tels2[:6])
        rex = x.results.rex
        self.assertEqual(type(rex), list)
        d = dict(zip(rex, x.coverage()))
        self.assertEqual(d,
                         {
                            r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$': 9,
                            r'^\(\d{3,4}\) \d{3,4} \d{4}$': 6,
                         })
        d = dict(zip(rex, x.coverage(dedup=True)))
        self.assertEqual(d,
                         {
                            r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$': 5,
                            r'^\(\d{3,4}\) \d{3,4} \d{4}$': 4,
                         })

    def test_incremental_coverage_tels2_dedup(self):
        x = Extractor(self.tels2 + self.tels2[:6])
        rex = x.results.rex
        od = x.incremental_coverage(dedup=True)
        self.assertEqual(od,
                         OrderedDict((
                            (r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$', 5),
                            (r'^\(\d{3,4}\) \d{3,4} \d{4}$', 4),
                         )))

    tels3 = [
        '0131-222-9876',
        '0207.987.2287'
    ]

    def test_tels3(self):
        r = extract(self.tels3, as_object=True)
        self.assertEqual(r.warnings, [])
        self.assertEqual(r.results.refrags,
                         [[(u'\\d{4}', True),
                           (u'[\\-\\.]', False),
                           (u'\\d{3}', True),
                           (u'[\\-\\.]', False),
                            (u'\\d{4}', True),
                          ]])
        self.check_result(r.results.rex, [r'^\d{4}[\-\.]\d{3}[\-\.]\d{4}$'],
                          self.tels3)

    tels4 = [
        '222-678-8834',
        '321-123-1234',
        '212-988-0321',
        '191-777-2043'
    ]
    def test_tels4(self):
        x = extract(self.tels4)
        self.check_result(x, [r'^\d{3}\-\d{3}\-\d{4}$'], self.tels4)


    tels5 = [
        '212-988-0321',
        '987-654-3210',
        '476 123 8829',
        '123 456 7890',
        '1 701 734 9288',
        '1 177 441 7712',
        '(617) 222 0529',
        '(222) 111 9276',
    ]
    def test_tels5(self):
#        print(Extractor(self.tels5))
        x = extract(self.tels5)
        rexes = [
            r'^\d{3} \d{3} \d{4}$',
            r'^\d{3}\-\d{3}\-\d{4}$',
            r'^\(\d{3}\) \d{3} \d{4}$',
            r'^1 \d{3} \d{3} \d{4}$',
        ]
        self.check_result(x, rexes, self.tels5)

    def test_tels_1to5(self):
        tels = self.tels1 + self.tels2 + self.tels3 + self.tels4 + self.tels5
        x = extract(tels)
        rexes = [
            r'^\d{3} \d{3} \d{4}$',
            r'^\d{3,4}[\-\.]\d{3}[\-\.]\d{4}$',
            r'^\(\d{3,4}\) \d{3,4} \d{4}$',
            r'^1 \d{3} \d{3} \d{4}$',
            r'^\+\d{1,2} \d{2,3} \d{3,4} \d{4}$',
        ]
        self.check_result(x, rexes, tels)

    urls1 = [
        'http://www.stochasticsolutions.com/',
        'http://apple.com/',
        'http://stochasticsolutions.com/',
        'http://www.stochasticsolutions.co.uk/',
        'http://www.google.co.uk/',
        'http://www.google.com',
        'http://www.google.com/',
        'http://www.stochasticsolutions.com',
        'http://web.stochasticsolutions.com',
        'https://www.stochasticsolutions.com',
        'http://tdda.info',
        'http://web.web',
    ]

    POSTCODES = [
        'EH3 1LH',
        'G4 2BP',
    ]
    def test_POSTCODES(self):
        self.assertEqual(extract(self.POSTCODES),
                         [r'^[A-Z]{1,2}\d \d[A-Z]{2}$'])
        # Improved answer
        # Previously
        #    [r'^[A-Z0-9]{2,3} [A-Z0-9]{3}$'])


    Postcodes = [
        'EH3 1LH',
        'g4 2bp',
    ]
    def test_Postcodes(self):
        self.assertEqual(extract(self.Postcodes),
                         [r'^[A-Za-z0-9]{2,3} [A-Za-z0-9]{3}$'])

    postcodes = [
        'eh3 1lh',
        'g4 2bp',
    ]
    def test_Postcodes2(self):
        self.assertEqual(extract(self.postcodes),
                         [r'^[a-z]{1,2}\d \d[a-z]{2}$'])
        # Improved answer.
        # Previously:
        #     [r'^[a-z0-9]{2,3} [a-z0-9]{3}$'])

    postCODES = [
        'eh3 1LH',
        'g4 2BP',
    ]
    def test_postCODES(self):
        self.assertEqual(extract(self.postCODES),
                         [r'^[a-z]{1,2}\d \d[A-Z]{2}$'])
        # Improved answer.
        # Previously:
        #     [r'^[a-z0-9]{2,3} [A-Z0-9]{3}$'])

    POSTcodes = [
        'EH3 1lh',
        'G4 2bp',
    ]
    def test_POSTcodes(self):
        self.assertEqual(extract(self.POSTcodes),
                         [r'^[A-Z]{1,2}\d \d[a-z]{2}$'])
#                         [r'^[A-Z0-9]{2,3} [a-z0-9]{3}$'])


    names1 = [
        'Euclid',
        'Homer',
        'Plato',
    ]

    names1L = names1 + ['Socrates']

    names2 = [
        'Albert Einstein',
        'Richard Feynman',
        'Miles Davis',
    ]
    names3 = [
        'James Clerk Maxwell',
        'Ralph Waldo Emerson',
        'Carl Friedrich Gauss',
    ]

    namesAU = names2 + [
        'Emmy Nöther'
    ]

    namesUA = names2 + [
        'Stanisław Mazur'
    ]

    namesUAU = names3 + [
        'Émilie du Châtelet'
    ]

    names_dot_initial = [
        'John F. Kennedy',
        'George W. Bush',
    ]

    def test_names1(self):
        self.assertEqual(extract(self.names1), [r'^[A-Z][a-z]{4,5}$'])


    def test_names1L(self):
        self.assertEqual(extract(self.names1L), [r'^[A-Z][a-z]+$'])


    def test_names2(self):
        self.assertEqual(extract(self.names2),
                         [r'^[A-Z][a-z]{4,6} [A-Z][a-z]+$'])


    def test_names3(self):
        self.assertEqual(extract(self.names3),
                         [r'^[A-Z][a-z]{3,4} [A-Z][a-z]+ [A-Z][a-z]{4,6}$'])

    @unittest.skipIf(not UNICHRS, 'Unicode handling off')
    def test_namesAU(self):
        self.assertEqual(extract(self.namesAU),
                        [r'^[A-Z][a-z]+ [^\W0-9_]+$'])

    @unittest.skipIf(not UNICHRS, 'Unicode handling off')
    def test_namesAU(self):
        self.assertEqual(extract(self.namesUA),
                         [r'^[^\W0-9_]+ [A-Z][a-z]+$'])

    @unittest.skipIf(not UNICHRS, 'Unicode handling off')
    def test_namesUAU(self):
        self.assertEqual(extract(self.namesUAU),
                         [r'^[^\W0-9_]{4,6} [A-Za-z]+ [^\W0-9_]+$'])

    def test_names_dot_initial(self):
        self.assertEqual(extract(self.names_dot_initial),
                         [r'^[A-Z][a-z]{3,5} [A-Z]\. [A-Z][a-z]+$'])

    def test_names1L23(self):
        self.assertEqual(extract(self.names1L + self.names2 + self.names3),
                         [r'^[A-Z][a-z]+$',
                          r'^[A-Z][a-z]{4,6} [A-Z][a-z]+$',
                          r'^[A-Z][a-z]{3,4} [A-Z][a-z]+ [A-Z][a-z]{4,6}$'])

    def test_names1L23_dot_initial(self):
        self.assertEqual(extract(self.names1L + self.names2 + self.names3
                                 + self.names_dot_initial),
                         [r'^[A-Z][a-z]+$',
                          r'^[A-Z][a-z]{4,6} [A-Z][a-z]+$',
                          r'^[A-Z][a-z]{3,4} [A-Z][a-z]+ [A-Z][a-z]{4,6}$',
                          r'^[A-Z][a-z]{3,5} [A-Z]\. [A-Z][a-z]+$'])

    abplus = ['ab', 'abb', 'abbb', 'abbbbb', 'abbbbbbb',
              'ab', 'abbbbbbb', 'abbbb', 'ab', 'abbbb',]
    aplusbplus = ['ab', 'abb', 'abbb', 'abbbbb', 'aaaaaaaaaaabbbbbbb',
                  'aab', 'aaabb', 'aaabbbb', 'ab', 'abbbb',]

    def test_abplus(self):
        self.assertEqual(extract(self.abplus), [r'^ab+$'])

    def test_urls1(self):
        self.assertEqual(extract(self.aplusbplus), [r'^a+b+$'])

#        print()
#        x = Extractor(self.urls1, verbose=True)
#        x = Extractor(self.urls1, verbose=True)
#        print(str(x))
        self.assertEqual(set(extract(self.urls1, variableLengthFrags=False)),
                         set([r'^http\:\/\/www\.[a-z]+\.com\/$',
                              r'^http\:\/\/[a-z]{3,4}\.[a-z]{3,4}$',
                              r'^http\:\/\/[a-z]+\.com\/$',
                              r'^[a-z]{4,5}\:\/\/[a-z]{3}\.[a-z]+\.com$',
                              r'^http\:\/\/www\.[a-z]+\.co\.uk\/$',]))

        self.assertEqual(set(extract(self.urls1, variableLengthFrags=True)),
                         set([r'^http\:\/\/[a-z]{3,4}\.[a-z]{3,4}$',
                              r'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
                              r'^http\:\/\/www\.[a-z]+\.com\/$',
                              r'^http\:\/\/[a-z]+\.com\/$',
                              r'^https?\:\/\/w{1,3}e?b?\.[a-z]+\.com$',]))


        # Sorted by length, these forms are:These are All:
        #
        #    C+.+C+.C+
        #    C+.+C+.C+.
        #    C+.+C+.C+.C+
        #    C+.+C+.C+.C+.
        #    C+.+C+.C+.C+.C+.

        # So: C+.+C+.C+(.C+)*.?
        # But that's a bit general!


        # Really want:
        #    '^https?\:\/\/([a-z]+\.)+[a-z]+\/?$'
        # Quite a way to go!
        #   - Small categoricals (http|https)
        #   - Related small categoricals (http|https) --> https?)
        #   - {6-19} --> +  (but when?)
        #   -  (C|C.C|C.C.C) --> (C.)+C   (i.e. concept of separation
        #                                  as opposed to terminators)


    urls2 = [
        'stochasticsolutions.com/',
        'apple.com/',
        'stochasticsolutions.com/',  # actual duplicate
        'http://www.stochasticsolutions.co.uk/',
        'http://www.google.co.uk/',
        'http://www.google.com',
        'http://www.google.com/',
        'http://www.guardian.co.uk/',
        'http://www.guardian.com',
        'http://www.guardian.com/',
        'http://www.stochasticsolutions.com',
        'web.stochasticsolutions.com',
        'https://www.stochasticsolutions.com',
        'tdda.info',
        'gov.uk',
        'http://web.web',
    ]

    def test_urls2(self):

#        print()
#        x = Extractor(self.urls2, verbose=True)
#        x = Extractor(self.urls2, variableLengthFrags=True)
#        print(str(x))
        self.assertEqual(set(extract(self.urls2, variableLengthFrags=False)), {
            r'^[a-z]{3,4}\.[a-z]{2,4}$',
            r'^[a-z]+\.com\/$',
            r'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
            r'^[a-z]{4,5}\:\/\/www\.[a-z]+\.com$',
            r'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
            r'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
        })
        self.assertEqual(set(extract(self.urls2, variableLengthFrags=True)), {
            r'^[a-z]{3,4}\.[a-z]{2,4}$',
            r'^[a-z]+\.com\/$',
            r'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
            r'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
            r'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
            r'^https?\:\/\/www\.[a-z]+\.com$',
        })

    def test_incremental_coverage_urls2(self):
        x = Extractor(self.urls2, variableLengthFrags=False)
        od = x.incremental_coverage()
        expected = OrderedDict((
                      (u'^[a-z]{4,5}\\:\\/\\/www\\.[a-z]+\\.com$', 4),
                      (u'^[a-z]+\\.com\\/$', 3),
                      (u'^http\\:\\/\\/www\\.[a-z]+\\.co\\.uk\\/$', 3),
                      (u'^[a-z]{3,4}[\\.\\/\\:]{1,3}[a-z]+\\.[a-z]{3}$', 2),
                      (u'^[a-z]{3,4}\\.[a-z]{2,4}$', 2),
                      (u'^http\\:\\/\\/www\\.[a-z]{6,8}\\.com\\/$', 2)))
        self.assertEqual(od, expected)
        self.assertEqual(x.n_examples(), 16)

        expected_dd = OrderedDict((
                         (u'^[a-z]{4,5}\\:\\/\\/www\\.[a-z]+\\.com$', 4),
                         (u'^http\\:\\/\\/www\\.[a-z]+\\.co\\.uk\\/$', 3),
                         (u'^[a-z]+\\.com\\/$', 2),
                         (u'^[a-z]{3,4}[\\.\\/\\:]{1,3}[a-z]+\\.[a-z]{3}$', 2),
                         (u'^[a-z]{3,4}\\.[a-z]{2,4}$', 2),
                         (u'^http\\:\\/\\/www\\.[a-z]{6,8}\\.com\\/$', 2)))
        od = x.incremental_coverage(dedup=True)
        self.assertEqual(od, expected_dd)
        self.assertEqual(x.n_examples(dedup=True), 15)


        x = Extractor(self.urls2 * 2, variableLengthFrags=False)
        doubled = OrderedDict([(k, n * 2) for k, n in expected.items()])
        od = x.incremental_coverage()
        self.assertEqual(od, doubled)
        self.assertEqual(x.n_examples(), 32)

        od = x.incremental_coverage(dedup=True)
        self.assertEqual(od, expected_dd)
        self.assertEqual(x.n_examples(dedup=True), 15)

    def test_full_incremental_coverage(self):
        freqs = {
            'One': 1,
            'one': 1,
            'two': 2,
            'three': 3,
            'four': 4,
            'five': 5,
            'six': 6,
            'seven': 7,
        }
        patterns = ['^f.+$', '^.{3}$', '^[st].+$']
        results = rexpy.rex_full_incremental_coverage(patterns, freqs)

#        for k in results:
#            print("            (u'%s',\n             rexpy.%s),"
#                  % (k, results[k]))
        expected = OrderedDict((
            (u'^[st].+$',
             Coverage(n=18,      # 2 + 3 + 6 + 7,
                            n_uniq=4,  # two, three, six, seven
                            incr=18,
                            incr_uniq=4,
                            index=2)),
            (u'^f.+$',
             Coverage(n=9,        # 4 + 5
                            n_uniq=2,   # four, five
                            incr=9,     # four (4), five (5)
                            incr_uniq=2,
                            index=0)),
            (u'^.{3}$',
             Coverage(n=10,      # 1 + 1 + 2 + 6
                            n_uniq=4,  # One, one, two, six
                            incr=2,    # One (1), one (1)
                            incr_uniq=2,
                            index=1)),
        ))
        self.assertEqual(results, expected)

        results = rexpy.rex_full_incremental_coverage(patterns, freqs,
                                                      dedup=True)
        expected = OrderedDict((
            (u'^.{3}$',
             Coverage(n=10,       # 1 + 1 + 2 + 6
                            n_uniq=4,   # One, one, two, six
                            incr=10,    # One (1), one (1), two (2), six (6)
                            incr_uniq=4,
                            index=1)),
            (u'^[st].+$',
             Coverage(n=18,       # 2 + 3 + 6 + 7,
                            n_uniq=4,   # two, three, six, seven
                            incr=10,    # three (3), seven (7)
                            incr_uniq=2,
                            index=2)),
            (u'^f.+$',
             Coverage(n=9,        # 4 + 5
                            n_uniq=2,   # four, five
                            incr=9,     # four (4), five (5)
                            incr_uniq=2,
                            index=0)),
        ))
        self.assertEqual(results, expected)

    def test_full_incremental_coverage_urls2(self):
        x = Extractor(self.urls2, variableLengthFrags=False)
        od = x.full_incremental_coverage()
        expected = OrderedDict((
            (u'^[a-z]{4,5}\:\/\/www\.[a-z]+\.com$',
             Coverage(n=4, n_uniq=4, incr=4, incr_uniq=4, index=3)),
            (u'^[a-z]+\.com\/$',
             Coverage(n=3, n_uniq=2, incr=3, incr_uniq=2, index=1)),
            (u'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
             Coverage(n=3, n_uniq=3, incr=3, incr_uniq=3, index=5)),
            (u'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=2)),
            (u'^[a-z]{3,4}\.[a-z]{2,4}$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=0)),
            (u'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=4)),
        ))

        self.assertEqual(od, expected)
        self.assertEqual(x.n_examples(), 16)
        expected_dd = OrderedDict((
            (u'^[a-z]{4,5}\:\/\/www\.[a-z]+\.com$',
             Coverage(n=4, n_uniq=4, incr=4, incr_uniq=4, index=3)),
            (u'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
             Coverage(n=3, n_uniq=3, incr=3, incr_uniq=3, index=5)),
            (u'^[a-z]+\.com\/$',
             Coverage(n=3, n_uniq=2, incr=3, incr_uniq=2, index=1)),
            (u'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=2)),
            (u'^[a-z]{3,4}\.[a-z]{2,4}$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=0)),
            (u'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=4)),
        ))

        od = x.full_incremental_coverage(dedup=True)
        self.assertEqual(od, expected_dd)
        self.assertEqual(x.n_examples(dedup=True), 15)

        x = Extractor(self.urls2 * 2, variableLengthFrags=False)
        doubled = OrderedDict((
            (u'^[a-z]{4,5}\:\/\/www\.[a-z]+\.com$',
             Coverage(n=8, n_uniq=4, incr=8, incr_uniq=4, index=3)),
            (u'^[a-z]+\.com\/$',
             Coverage(n=6, n_uniq=2, incr=6, incr_uniq=2, index=1)),
            (u'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
             Coverage(n=6, n_uniq=3, incr=6, incr_uniq=3, index=5)),
            (u'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=2)),
            (u'^[a-z]{3,4}\.[a-z]{2,4}$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=0)),
            (u'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=4)),
        ))
        od = x.full_incremental_coverage()
        self.assertEqual(od, doubled)
        self.assertEqual(x.n_examples(), 32)

        od = x.full_incremental_coverage(dedup=True)

        expected_doubled_dd = OrderedDict((
            (u'^[a-z]{4,5}\:\/\/www\.[a-z]+\.com$',
             Coverage(n=8, n_uniq=4, incr=8, incr_uniq=4, index=3)),
            (u'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
             Coverage(n=6, n_uniq=3, incr=6, incr_uniq=3, index=5)),
            (u'^[a-z]+\.com\/$',
             Coverage(n=6, n_uniq=2, incr=6, incr_uniq=2, index=1)),
            (u'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=2)),
            (u'^[a-z]{3,4}\.[a-z]{2,4}$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=0)),
            (u'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=4)),
        ))
        self.assertEqual(od, expected_doubled_dd)
        self.assertEqual(x.n_examples(dedup=True), 15)

    def test_full_incremental_coverage_urls2_var(self):
        x = Extractor(self.urls2, variableLengthFrags=True)
        od = x.full_incremental_coverage()
        expected = OrderedDict((
            (u'^https?\:\/\/www\.[a-z]+\.com$',
             Coverage(n=4, n_uniq=4, incr=4, incr_uniq=4, index=4)),
            (u'^[a-z]+\.com\/$',
             Coverage(n=3, n_uniq=2, incr=3, incr_uniq=2, index=1)),
            (u'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
             Coverage(n=3, n_uniq=3, incr=3, incr_uniq=3, index=5)),
            (u'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=2)),
            (u'^[a-z]{3,4}\.[a-z]{2,4}$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=0)),
            (u'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
             Coverage(n=2, n_uniq=2, incr=2, incr_uniq=2, index=3))
        ))

        x = Extractor(self.urls2 * 2, variableLengthFrags=True)
        doubled = OrderedDict((
            (u'^https?\:\/\/www\.[a-z]+\.com$',
             Coverage(n=8, n_uniq=4, incr=8, incr_uniq=4, index=5)),
            (u'^[a-z]+\.com\/$',
             Coverage(n=6, n_uniq=2, incr=6, incr_uniq=2, index=1)),
            (u'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
             Coverage(n=6, n_uniq=3, incr=6, incr_uniq=3, index=4)),
            (u'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3}$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=2)),
            (u'^[a-z]{3,4}\.[a-z]{2,4}$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=0)),
            (u'^http\:\/\/www\.[a-z]{6,8}\.com\/$',
             Coverage(n=4, n_uniq=2, incr=4, incr_uniq=2, index=3)),
        ))
        od = x.full_incremental_coverage()
        self.assertEqual(od, doubled)
        self.assertEqual(x.n_examples(), 32)


    def test_urls2_grouped(self):

#        print()
#        x = Extractor(self.urls2, verbose=True)
#        x = Extractor(self.urls2)
#        print(str(x))
        self.assertEqual(set(extract(self.urls2, tag=True,
                                     variableLengthFrags=False)), {
            r'^([a-z]{4,5})\:\/\/www\.([a-z]+)\.com$',
            r'^http\:\/\/www\.([a-z]{6,8})\.com\/$',
            r'^([a-z]{3,4})\.([a-z]{2,4})$',
            r'^([a-z]{3,4})[\.\/\:]{1,3}([a-z]+)\.([a-z]{3})$',
            r'^([a-z]+)\.com\/$',
            r'^http\:\/\/www\.([a-z]+)\.co\.uk\/$',
        })
        self.assertEqual(set(extract(self.urls2, tag=True,
                                     variableLengthFrags=True)), {
            r'^http\:\/\/www\.([a-z]{6,8})\.com\/$',
            r'^([a-z]{3,4})\.([a-z]{2,4})$',
            r'^([a-z]{3,4})[\.\/\:]{1,3}([a-z]+)\.([a-z]{3})$',
            r'^https?\:\/\/www\.([a-z]+)\.com$',
            r'^([a-z]+)\.com\/$',
            r'^http\:\/\/www\.([a-z]+)\.co\.uk\/$',
        })

    def test_urls_all(self):

#        print()
#        x = Extractor(self.urls2, verbose=True)
#        x = Extractor(self.urls1 + self.urls2)
#        print(str(x))
        self.assertEqual(set(extract(self.urls1 + self.urls2,
                                     variableLengthFrags=False)), {
            r'^[a-z]{3,4}\.[a-z]{2,4}$',
            r'^[a-z]+\.com\/$',
            r'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3,4}$',
            r'^http\:\/\/[a-z]+\.com\/$',
            r'^[a-z]{4,5}\:\/\/[a-z]{3}\.[a-z]+\.com$',
            r'^http\:\/\/www\.[a-z]+\.com\/$',
            r'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
        })

        self.assertEqual(set(extract(self.urls1 + self.urls2,
                                     variableLengthFrags=True)), {
            r'^[a-z]{3,4}\.[a-z]{2,4}$',
            r'^[a-z]+\.com\/$',
            r'^[a-z]{3,4}[\.\/\:]{1,3}[a-z]+\.[a-z]{3,4}$',
            r'^http\:\/\/[a-z]+\.com\/$',
            r'^http\:\/\/www\.[a-z]+\.com\/$',
            r'^http\:\/\/www\.[a-z]+\.co\.uk\/$',
            r'^https?\:\/\/w{1,3}e?b?\.[a-z]+\.com$'
        })

    def test_agents(self):
        # This is really just a check that it doesn't bomb out, for the
        # moment. It's certainly not finding good REs at this point!
        examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'examples')
        agents_path = os.path.join(examples_dir, 'agents9.txt')
        with open(agents_path) as f:
            examples = f.read().splitlines()
        r = extract(examples, as_object=True)
        self.assertEqual(set(r.results.rex), {
            r'^Mozilla\/4\.0 \(compatible\; MSIE 8\.0\; Windows NT '
            r'6\.0\; Trident\/4\.0\;   Acoo Browser\; GTB5\; '
            r'Mozilla\/4\.0 \(compatible\; MSIE 6\.0\; Windows '
            r'NT 5\.1\;   SV1\) \; InfoPath\.1\; \.NET CLR '
            r'3\.5\.30729\; \.NET CLR 3\.0\.30618\)$',

            r'^Mozilla\/5\.0 \(compatible\; ABrowse 0\.4\; Syllable\)$',

            r'^Mozilla\/5\.0 \(compatible\; U\; ABrowse 0\.6\; '
            r'{1,2}Syllable\) AppleWebKit\/420\+ \(KHTML\, like Gecko\)$',

            r'^Mozilla\/5\.0 \(compatible\; MSIE 8\.0\; Windows '
            r'NT 6\.0\; Trident\/4\.0\; Acoo Browser 1\.98\.744\; '
            r'\.NET CLR {1,3}3\.5\.30729\)$',

            r'^Mozilla\/4\.0 \(compatible\; MSIE 7\.0\; Windows '
            r'NT 6\.0\; Acoo Browser\; SLCC1\;   \.NET CLR '
            r'2\.0\.50727\; Media Center PC 5\.0\; \.NET CLR '
            r'3\.0\.04506\)$',

            r'^Mozilla\/4\.0 \(compatible\; MSIE 8\.0\; Windows '
            r'NT 5\.1\; Trident\/4\.0\; SV1\; Acoo Browser\; '
            r'\.NET CLR 2\.0\.50727\; \.NET CLR 3\.0\.4506\.2152\; '
            r'\.NET CLR 3\.5\.30729\; Avant Browser\)$',

            r'^Mozilla\/4\.0 \(compatible\; MSIE 7\.0\; Windows '
            r'NT 6\.0\; Acoo Browser\; GTB5\; Mozilla\/4\.0 '
            r'\(compatible\; MSIE 6\.0\; Windows NT 5\.1\; '
            r'SV1\) \; Maxthon\; InfoPath\.1\; \.NET CLR 3\.5\.30729\; '
            r'\.NET CLR 3\.0\.30618\)$',
        })
        self.assertEqual(r.n_too_many_groups, 1)
        self.assertEqual(r.warnings[0], '1 string assigned to .{m,n} for '
                                        'needing "too many" groups.')

    def testmflag(self):
        patterns = ('a.1', 'b_2', 'c-3')
        expected = ['^c\-3$', r'^([a-z])([A-Z\.\_])(\d)$']
        r = extract(patterns, tag=True, extra_letters='._')
        self.assertEqual(r, expected)

    def testmflag2(self):
        patterns = ('a-1', 'c-3')
        expected = [r'^([a-z])\-(\d)$']
        r = extract(patterns, tag=True, extra_letters='._')
        self.assertEqual(r, expected)

    def testFindOuterCaptureGroups(self):
        r = re.compile('^(([A-Z]+) [1-5])([^\W_]+)$', re.U)
        m = re.match(r, 'THIS 3aéAB')
        self.assertEqual(is_outer_group(m, 1), True)
        self.assertEqual(is_outer_group(m, 2), False)
        self.assertEqual(is_outer_group(m, 3), True)

        f = group_map_function(m, 2)
        self.assertEqual(f(1), 1)
        self.assertEqual(f(2), 3)
        self.assertRaises(KeyError, f, 3)

        r = re.compile('^aaa([A-Z]+)bb$', re.U)
        m = re.match(r, 'aaaBBbb')
        f = group_map_function(m, 2)
        self.assertEqual(f(1), 1)
        self.assertRaises(KeyError, f, 2)

        regex = '@ (a(b)c) d (e(f(g)h(i(j)k)l)m) n (o) p (q(r)s) t'
        r = re.compile(regex, re.U)
        m = re.match(r, '@ abc d efghijklm n o p qrs t')
        f = group_map_function(m, 4)
        self.assertEqual(f(1), 1)
        self.assertEqual(f(2), 3)
        self.assertEqual(f(3), 8)
        self.assertEqual(f(4), 9)
        self.assertRaises(KeyError, f, 5)


    @unittest.skipIf(pandas is None, 'No pandas here')
    def testpdextract(self):
        df = pd.DataFrame({'a3': ["one", "two", pd.np.NaN],
                           'a45': ['three', 'four', 'five']})

        re3 = pdextract(df['a3'])
        re45 = pdextract(df['a45'])
        re345 = pdextract([df['a3'], df['a45']])

        self.assertEqual(re3, ['^[a-z]{3}$'])
        self.assertEqual(re45, ['^[a-z]{4,5}$'])
        self.assertEqual(re345, ['^[a-z]{3,5}$'])

    @unittest.skipIf(pandas is None, 'No pandas here')
    def testpdextract2(self):
        df = pd.DataFrame({'ab': ["one", True, pd.np.NaN]})
        self.assertRaisesRegex(ValueError, 'Non-null, non-string',
                               pdextract, df['ab'])


def print_ordered_dict(od):
    print()
    print('        expected = OrderedDict((')
    for k in od:
        print("            (u'%s',\n             rexpy.%s),"
              % (k, od[k]))
    print('        ))')


C = UNIC if UNICHRS else 'C'
def CtoUC(s):
    if UNICHRS:
        return s.replace('C', UNIC)
    else:
        return s



if sys.version_info[0] < 3:
    # Quieten down Python3's vexatious complaining
    TestExtraction.assertRaisesRegex = TestExtraction.assertRaisesRegexp

    # def testextractcli(self):
    #     examples_dir = os.path.join(os.path.abspath(__file__), 'examples')
    #     ids_path = os.path.join(examples_dir, 'ids.txt')
    #     params = get_params(ids_path)
    #     main(params)



if __name__ == '__main__':
    unittest.main()

