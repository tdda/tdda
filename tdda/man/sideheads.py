import sys
import re

seealso = False
print('.na')  # turn off justification
print('.nr l 79')  # set register l to 79
print('.ll \\nl')  # set line length to 79
for line in sys.stdin.readlines():
    if line.startswith('.SH'):
        line = f'.SH\n{line[4:]}\n'
    elif not line.startswith('.'):
        line = f'  {line}'
    if 'SEE ALSO' in line:
        seealso = True
    if seealso:
        line = line.replace('-', ' ').replace(',', '')
        pos = line.find('(')
        if pos > 0 and '](' not in line:
            line = line[:pos] + '\n'
    print(line, end='')
