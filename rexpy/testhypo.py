#
# testing rexpy with hypothesis
#
# see hypothesis.works
#
# requires hypothesis to be installed, via "pip install hypothesis".
#

import unittest
import re

from tdda.rexpy import Extractor

try:
    from hypothesis import given, settings, HealthCheck
    from hypothesis.strategies import text, integers, composite

    @composite
    def list_of_strings(draw):
        return [draw(text(min_size=1, average_size=70))
                for i in range(draw(integers(min_value=0, max_value=100)))]

    class TestRexpyHypothetically(unittest.TestCase):
        @given(list_of_strings())
        @settings(suppress_health_check=[HealthCheck.too_slow])
        def test_matches(self, strings):
            x = Extractor(strings)
            for rex in x.results.rex:
                r = re.compile(rex, flags=re.DOTALL|re.UNICODE)
                matches = [r.match(e) for e in strings]
                self.assertTrue(any(matches))

except ImportError:
    pass


if __name__ == '__main__':
    unittest.main()

