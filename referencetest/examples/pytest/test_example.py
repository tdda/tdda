
import pytest

from tdda.referencetest import referencepytest

def my_function(s):
    return s


@pytest.fixture(scope='module')
def ref():
    r = referencepytest.ref()
    r.set_data_location(None, '../../tests/testdata')
    r.set_data_location('graph', '../../tests/testdata')
    return r

def test_my_table_function(ref):
    result = my_function('a single line')
    ref.assertStringCorrect(result, 'single.txt', kind='table')

def test_my_graph_function(ref):
    result = my_function('a single line')
    ref.assertStringCorrect(result, 'single.txt', kind='graph')

