from __future__ import print_function

import difflib
import re
import sys

from collections import defaultdict

from tdda.rexpy import extract

LINE_NUMBER_RE = re.compile(r'^@@\s+\-(\d+),\d+\s+\+(\d+),\d+\s+@@$')
TOGETHER = True

def diffrex(left_path, right_path):
    with open(left_path) as f:
        left_lines = f.readlines()
    with open(right_path) as f:
        right_lines = f.readlines()
    L = []
    R = []
    pairs = []
    prev_source = None
    left_num = right_num = None
    for i, line in enumerate(difflib.unified_diff(left_lines, right_lines,
                                                  left_path, right_path)):
        if i < 2:
            continue
        line_source = line[:1]
        if line_source == '@':
            m = re.match(LINE_NUMBER_RE, line)
            if not m:
                raise Exception('Bad line %s' % line[:-1])
            left_num, right_num = int(m.group(1)), int(m.group(2))
        elif (line_source == prev_source
               or line_source == '+' and prev_source == '-'
               or line_source == '-' and prev_source == ' '):
            if line_source == '-':  # left
                L.append(line)
            elif line_source == '+':  # right
                R.append(line)
        else:
            if line_source == ' ':  # common line
                add_pairs(pairs, L, R, left_num, right_num)
                L = []
                R = []
            else:
                print('DID NOT EXPECT THIS', prev_source, line_source)
        prev_source = line_source
    add_pairs(pairs, L, R, left_num, right_num)

    if pairs:
        if TOGETHER:
            lefts = [p[0][1:-1] for p in pairs if p[0]]
            rights = [p[1][1:-1] for p in pairs if p[1]]
            rexes = extract(lefts + rights)
            print('Patterns:')
            for r in rexes:
                print(r)
        else:
            rexes = defaultdict(list)
            fails = []
            for (left, right, left_num, right_num) in pairs:
                print(left, end='')
                print(right, end='')
                patterns = extract([left[1:-1], right[1:-1]])
                if len(patterns) == 1:
                    rex = patterns.pop()[1:-1]
                    print('/%s' % rex)
                    rexes[rex].append((left_num, right_num))
                else:
                    print('*** Could not find RE.')
                    fails.append((left, right))
                print()
            print('%d pattern%s for %d line pair%s'
                  % (len(rexes), 's' if len(rexes) != 1 else '',
                     len(pairs), 's' if len(pairs) != 1 else ''))
            for r, lines in sorted(rexes.items()):
                print(' ', r)
                print('     ', lines)
            if fails:
                print()
            print('%d pair%s of lines failed:'
                  % (len(fails), 's' if len(fails) != 1 else ''))
            for left, right in fails:
                print(left)
                print(right)
                print()
    else:
        print('(no diffs)')


def add_pairs(pairs, L, R, left_num, right_num):
    if L or R:
        for i in range(max(len(L), len(R))):
            pairs.append((L[i] if i < len(L) else '',
                          R[i] if i < len(R) else '',
                          (left_num + i) if i < len(L) else 0,
                          (right_num + i) if i < len(R) else 0))


if __name__ == '__main__':
    diffrex(sys.argv[1], sys.argv[2])
