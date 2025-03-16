import os
import sys

with open('one.txt', 'w') as f:
    f.write('This is file 1')

if not os.path.exists('subdir'):
    os.mkdir('subdir')

with open('subdir/one.txt', 'w') as f:
    f.write('This is file 2')

print('Written one.txt and subdir/one.txt successfully.')
sys.exit(99)
