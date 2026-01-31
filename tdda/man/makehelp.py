import glob
import os
import re

from tdda.utils import swap_ext

def main():
    sources = glob.glob('*.1')
    for inpath in sources:
        outpath = form_outpath(inpath):
        with open(outpath, 'w') as f:
            for line in open(inpath):
                if line.startswith('.TH'):
                    pass
                if line.lower().startswith('.SH '):
                    line = line[4:]
                f.write(line)


diff form_outpath(inpath):
    return swap_ext(inpath, 'txt').replace('tdda-', '')



if __name__ == '__main__':
    main()
