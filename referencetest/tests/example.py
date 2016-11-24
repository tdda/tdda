# -*- coding: utf-8 -*-

import sys
from tdda.referencetest import ReferenceTestCase

class my_module(object):
    @staticmethod
    def my_function():
        pass


class MyTest(ReferenceTestCase):
    def __init__(self, *args, **kwargs):
        ReferenceTestCase.__init__(self, *args, **kwargs)
        self.set_data_location(None, '/data')

    def test_my_table_function(self):
        result = my_module.my_function()
        self.assertStringCorrect(result, 'result.txt', kind='table')

    def test_my_graph_function(self):
        result = my_module.my_function()
        self.assertStringCorrect(result, 'result.txt', kind='graph')

if __name__ == '__main__':
    ReferenceTestCase.main()
