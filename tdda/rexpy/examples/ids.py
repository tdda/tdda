from tdda import rexpy

corpus = ['123-AA-971', '12-DQ-802', '198-AA-045', '1-BA-834']
results = rexpy.extract(corpus)
print('Number of regular expressions found: %d' % len(results))
for rex in results:
        print('   ' + rex)
