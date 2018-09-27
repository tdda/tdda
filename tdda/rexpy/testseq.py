from __future__ import print_function

from tdda.rexpy import extract
from tdda.rexpy.seq import common_string_sequence
from tdda.rexpy.relib import re

x = extract(['Roger', 'Coger', 'Doger'], tag=True, as_object=True)
print(x)

patternToExamples = x.pattern_matches()

sequences = []
for j, (pattern, examples) in enumerate(patternToExamples.items()):
    N = len(examples)
    if N < 1:
        print('%s:%s' % (pattern, examples))
    else:
        eparts = [re.match(x.results.rex[j], e).groups() for e in examples]
        nparts = len(eparts[0])
        for i in range(nparts):
            (L, R) = (eparts[0][i], eparts[1][i])
            n = 2
            s = common_string_sequence(L, R)
            while n < N and s != '':
                s = common_string_sequence(s, eparts[n][i])
                n += 1

            sequences.append(s)
print(sequences)

