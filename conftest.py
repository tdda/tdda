# pytest configuration: sets testing mode so colour is suppressed in output,
# matching the behaviour of running tests via testtdda.py.
from tdda.state import set_testing

set_testing(True)
