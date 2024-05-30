# -*- coding: utf-8 -*-

#
# Unit tests for reference data regeneration
#

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import os
import tempfile
import unittest

from tdda.referencetest.referencetest import ReferenceTest


class TestRegenerate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.gettempdir()

    def setUp(self):
        ReferenceTest.set_default_data_location(self.tmpdir)
        ReferenceTest.set_defaults(verbose=False)

    def tearDown(self):
        ReferenceTest.set_regeneration(regenerate=False)

    def test_regenerate_all(self):
        ReferenceTest.set_regeneration()
        ref = ReferenceTest(assert_fn=self.assertTrue)
        refname = 'regenerate_all.txt'
        reffile = os.path.join(self.tmpdir, refname)
        ref.assertStringCorrect('Start\nMiddle\nEnd\n', refname)
        with open(reffile) as f:
            self.assertEqual(f.read(), 'Start\nMiddle\nEnd\n')
        ref.assertStringCorrect('Completely different content', refname)
        with open(reffile) as f:
            self.assertEqual(f.read(), 'Completely different content')

    def test_regenerate_kinds(self):
        ReferenceTest.set_regeneration('csv')
        ref = ReferenceTest(assert_fn=self.assertTrue)
        txtname = 'regenerate.txt'
        csvname = 'regenerate.csv'
        txtfile = os.path.join(self.tmpdir, txtname)
        csvfile = os.path.join(self.tmpdir, csvname)
        with self.assertRaises(Exception):
            ref.assertStringCorrect(
                'End\nMiddle\nStart\n', txtname, kind='txt'
            )
        ref.assertStringCorrect('Start\nMiddle\nEnd\n', csvname, kind='csv')
        with open(csvfile) as f:
            self.assertEqual(f.read(), 'Start\nMiddle\nEnd\n')
        ref.assertStringCorrect(
            'Completely different content', csvname, kind='csv'
        )
        with open(csvfile) as f:
            self.assertEqual(f.read(), 'Completely different content')


if __name__ == '__main__':
    unittest.main()
