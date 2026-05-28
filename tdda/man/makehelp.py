import glob
import os
import re

from tdda.utils import swap_ext


def main():
    seealso = False
    sources = glob.glob('*.1')
    for inpath in sources:
        outpath = form_outpath(inpath)
        with open(outpath, 'w', encoding='utf-8') as f:
            for line in open(inpath, encoding='utf-8'):
                if line.startswith('.TH'):
                    continue
                if line.upper().startswith('.SH '):
                    line = line[4:]
                    seealso = 'SEE ALSO' in line
                else:
                    if line.strip():
                        line = f'    {line}'
                    if seealso:
                        line = line.replace('-', ' ').replace(',', '')
                        p = line.find('(')
                        if p > 1:
                            line = line[:p] + '\n'
                f.write(line)
        print(f'Written {outpath}')


def form_outpath(inpath):
    return swap_ext(inpath, 'txt').replace('tdda-', '')


if __name__ == '__main__':
    main()
