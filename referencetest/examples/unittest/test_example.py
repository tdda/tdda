# -*- coding: utf-8 -*-

import sys
from tdda.referencetest import ReferenceTestCase

class my_module(object):
    @staticmethod
    def my_function(s):
        return s


class MyTest(ReferenceTestCase):
    def __init__(self, *args, **kwargs):
        ReferenceTestCase.__init__(self, *args, **kwargs)
        self.set_data_location(None, '../../tests/testdata')
        self.set_data_location('graph', '../../tests/testdata')

    def test_my_table_function(self):
        result = my_module.my_function('a single line')
        self.assertStringCorrect(result, 'single.txt', kind='table')

    def test_my_graph_function(self):
        result = my_module.my_function('a single line')
        self.assertStringCorrect(result, 'single.txt', kind='graph')


if __name__ == '__main__':
    ReferenceTestCase.main()
