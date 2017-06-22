import re
from rexpy import extract
from seq import common_string_sequence

x = extract(['Roger', 'Coger', 'Doger'], tag=True, as_object=True)
print(x)

patternToExamples = x.pattern_matches()

for j, (pattern, examples) in enumerate(patternToExamples.items()):
    N = len(examples)
    if N < 1:
        print('%s:%s' % (pattern, examples))
    else:
        eparts = [re.match(x.results.rex[j], e).groups() for e in examples]
        nparts = len(eparts[0])
        for i in range(nparts):
            for example in eparts:
                (L, R) = (examples[i][0], examples[i][1])
                n = 2
                s = common_string_sequence(L, R)
                while n < N and s != '':
                    s = common_string_sequence(s, examples[i][n])
                    n += 1
            print('%s;%s:%s' % (x.results.rex[j], i, s))
