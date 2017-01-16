# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import datetime
import json
import math
import os
import time
import sys
import unittest

from tdda.constraints.base import (
    DatasetConstraints,
    Fields,
    FieldConstraints,
    MinConstraint,
    MaxConstraint,
    SignConstraint,
    TypeConstraint,
    MaxNullsConstraint,
    NoDuplicatesConstraint,
    AllowedValuesConstraint,
    MinLengthConstraint,
    MaxLengthConstraint,
    constraint_class,
    strip_lines,
)
TESTDATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'testdata')


class TestConstraints(unittest.TestCase):

    def test_constraint_repr(self):
        self.assertEqual(repr(MinConstraint(7)),
                         'MinConstraint(value=7, precision=None)')
        self.assertEqual(repr(MinConstraint('a')),
                         "MinConstraint(value='a', precision=None)")
        self.assertEqual(repr(MinConstraint('a', precision='closed')),
                         "MinConstraint(value='a', precision='closed')")
        self.assertEqual(repr(MinLengthConstraint(3)),
                         "MinLengthConstraint(value=3)")
        self.assertEqual(repr(MaxConstraint(-3)),
                         'MaxConstraint(value=-3, precision=None)')
        self.assertEqual(repr(MaxConstraint('KJ')),
                         "MaxConstraint(value='KJ', precision=None)")
        self.assertEqual(repr(MaxConstraint(4.2, precision='closed')),
                         "MaxConstraint(value=4.2, precision='closed')")
        self.assertEqual(repr(MaxLengthConstraint(0)),
                         "MaxLengthConstraint(value=0)")
        self.assertEqual(repr(SignConstraint('positive')),
                         "SignConstraint(value='positive')")
        self.assertEqual(repr(MaxNullsConstraint(0)),
                         "MaxNullsConstraint(value=0)")
        self.assertEqual(repr(NoDuplicatesConstraint()),
                         "NoDuplicatesConstraint(value=True)")
        self.assertEqual(repr(TypeConstraint('int')),
                         "TypeConstraint(value='int')")
        self.assertEqual(repr(TypeConstraint(['int', 'real'])),
                         "TypeConstraint(value=['int', 'real'])")
        self.assertEqual(repr(AllowedValuesConstraint(['a', 'b'])),
                         "AllowedValuesConstraint(value=['a', 'b'])")

    def test_constraint_class(self):
        goods = {
            'type': 'TypeConstraint',
            'min': 'MinConstraint',
            'min_length': 'MinLengthConstraint',
            'max': 'MaxConstraint',
            'max_length': 'MaxLengthConstraint',
            'sign': 'SignConstraint',
            'max_nulls': 'MaxNullsConstraint',
            'no_duplicates': 'NoDuplicatesConstraint',
            'allowed_values': 'AllowedValuesConstraint',
        }
        for k,v in goods.items():
            self.assertEqual(constraint_class(k), v)

    def testBadConstraints(self):
        self.assertRaisesRegexp(TypeError, 'unexpected keyword',
                                SignConstraint, precision='closed')
        self.assertRaises(AssertionError,
                          MinConstraint, 3, precision='unknown')
        self.assertRaises(AssertionError,
                          SignConstraint, 'not too positive')
        self.assertRaises(AssertionError,
                          TypeConstraint, 'float')
        self.assertRaises(AssertionError,
                          TypeConstraint, ['int', 'float'])
        self.assertRaises(AssertionError,
                          TypeConstraint, ['int', None])

    def testFieldConstraintsDict(self):
        c = FieldConstraints('one', [TypeConstraint('int'),
                                           MinConstraint(3),
                                           MaxConstraint(7),
                                           SignConstraint('positive'),
                                           MaxNullsConstraint(0),
                                           NoDuplicatesConstraint()])
        dfc = Fields([c])
        self.assertEqual(strip_lines(json.dumps(dfc.to_dict_value(),
                                                indent=4)),
                         '''{
    "one": {
        "type": "int",
        "min": 3,
        "max": 7,
        "sign": "positive",
        "max_nulls": 0,
        "no_duplicates": true
    }
}''')

        c = FieldConstraints('one', [TypeConstraint('int'),
                                     MinConstraint(3, precision='closed'),
                                     MaxConstraint(7, precision='fuzzy'),
                                     SignConstraint('positive'),
                                     MaxNullsConstraint(0),
                                     NoDuplicatesConstraint()])
        dfc = Fields([c])
        self.assertEqual(strip_lines(json.dumps(dfc.to_dict_value(),
                                                indent=4)),
                         '''{
    "one": {
        "type": "int",
        "min": {
            "value": 3,
            "precision": "closed"
        },
        "max": {
            "value": 7,
            "precision": "fuzzy"
        },
        "sign": "positive",
        "max_nulls": 0,
        "no_duplicates": true
    }
}''')

    def testload(self):
        path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        constraints = DatasetConstraints(loadpath=path)
#        print(constraints)


if __name__ == '__main__':
    unittest.main()
