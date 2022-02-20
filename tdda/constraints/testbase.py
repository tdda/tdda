# -*- coding: utf-8 -*-
import datetime
import json
import math
import os
import time
import sys
import unittest

from collections import OrderedDict

from tdda.referencetest.referencetestcase import ReferenceTestCase, tag

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
    sort_constraint_dict,
    InvalidConstraintSpecification
)

isPython2 = sys.version_info[0] < 3

TESTDATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            'testdata')


class TestConstraints(ReferenceTestCase):

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
        if isPython2:
            self.assertRaisesRegexp(TypeError, 'unexpected keyword',
                                    SignConstraint, precision='closed')
        else:
            self.assertRaisesRegex(TypeError, 'unexpected keyword',
                                   SignConstraint, precision='closed')
        self.assertRaises(InvalidConstraintSpecification,
                          MinConstraint, 3, precision='unknown')
        self.assertRaises(InvalidConstraintSpecification,
                          SignConstraint, 'not too positive')
        self.assertRaises(InvalidConstraintSpecification,
                          TypeConstraint, 'float')
        self.assertRaises(InvalidConstraintSpecification,
                          TypeConstraint, ['int', 'float'])
        self.assertRaises(InvalidConstraintSpecification,
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
        fields = ['index', 'evennulls', 'oddnulls', 'evens', 'odds',
                  'evenreals', 'oddreals', 'evenstr', 'oddstr',
                  'elevens', 'greek', 'binnedindex', 'binnedodds',
                  'basedate', 'evendates']
        constraints.sort_fields(fields)
        self.assertStringCorrect(constraints.to_json(), 'ddd.tdda',
                                 rstrip=True,
                                 ignore_substrings=['"as_at":',
                                                    '"local_time":',
                                                    '"utc_time":',
                                                    '"creator":',
                                                    '"host":',
                                                    '"user":',
                                                    '"tddafile":'])


TestConstraints.set_default_data_location(TESTDATA_DIR)


if __name__ == '__main__':
    unittest.main()
