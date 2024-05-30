# -*- coding: utf-8 -*-

#
# Unit tests for base ReferenceTest class functionality
#

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import os
import unittest

from tdda.referencetest.referencetest import ReferenceTest


class TestReferenceTest(unittest.TestCase):
    def testDefaultLocations(self):
        class ClassA(ReferenceTest):
            pass

        class ClassB(ClassA):
            pass

        class ClassC1(ClassB):
            pass

        class ClassC2(ClassB):
            pass

        class classZ(ReferenceTest):
            pass

        a = ClassA(None)
        b = ClassB(None)
        c1 = ClassC1(None)
        c2 = ClassC2(None)

        self.assertEqual(a._resolve_reference_path('x'), 'x')
        self.assertEqual(b._resolve_reference_path('x'), 'x')
        self.assertEqual(c1._resolve_reference_path('x'), 'x')
        self.assertEqual(c2._resolve_reference_path('x'), 'x')

        ClassA.set_default_data_location('t1')
        ClassB.set_default_data_location('t2')
        ClassC1.set_default_data_location('t3')

        a = ClassA(None)
        b = ClassB(None)
        c1 = ClassC1(None)
        c2 = ClassC2(None)

        self.assertEqual(
            a._resolve_reference_path('x'), os.path.join('t1', 'x')
        )
        self.assertEqual(
            b._resolve_reference_path('x'), os.path.join('t2', 'x')
        )
        self.assertEqual(
            c1._resolve_reference_path('x'), os.path.join('t3', 'x')
        )
        self.assertEqual(
            c2._resolve_reference_path('x'), os.path.join('t2', 'x')
        )


if __name__ == '__main__':
    unittest.main()
