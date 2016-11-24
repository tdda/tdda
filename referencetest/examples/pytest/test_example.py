
from tdda.referencetest.referencepytest import *

class my_module(object):
    @staticmethod
    def my_function(s):
        return s

set_data_location(None, '../../tests/testdata')
set_data_location('graph', '../../tests/testdata')

def test_my_table_function():
    result = my_module.my_function('a single line')
    assertStringCorrect(result, 'single.txt', kind='table')

def test_my_graph_function():
    result = my_module.my_function('a single line')
    assertStringCorrect(result, 'single.txt', kind='graph')

