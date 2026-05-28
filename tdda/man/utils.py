import os

from tdda.utils import swap_ext

TDDADIR = os.path.dirname(os.path.dirname(__file__))
MANDIR = os.path.join(TDDADIR, 'man')


def get_help(command):
    path = os.path.join(MANDIR, f'{command}.txt')
    tddapath = os.path.join(MANDIR, f'tdda-{command}.txt')
    if os.path.exists(path):  # tdda, rexpy
        with open(path, encoding='utf-8') as f:
            man = f.read()
    elif os.path.exists(tddapath):  # tdda discover etc.
        with open(tddapath, encoding='utf-8') as f:
            man = f.read()
    else:
        man = ''
    return f'{man.rstrip()}\n'


def print_help(command, stream):
    print(get_help(command), file=stream)
