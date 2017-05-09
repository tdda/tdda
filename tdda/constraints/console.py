from __future__ import print_function

import os
import sys
import unittest

from tdda.constraints import pddiscover, pdverify
from tdda.examples import copy_examples

HELP="""Use
    tdda discover  to perform constraint discovery
    tdda verify    to verify data against constraints
    tdda examples  to copy the example data and code
    tdda version   to print the TDDA version number
    tdda help      to print this help
    tdda test      to run the tdda library's tests."""


def main():
    if len(sys.argv) == 1:
        print(HELP, file=sys.stderr)
        sys.exit(1)
    name = sys.argv[1]
    if name in ('discover', 'disco'):
        pddiscover.main(sys.argv[1:])
    elif name in ('verify',):
        pdverify.main(sys.argv[1:])
    elif name in ('examples',):
        dest = sys.argv[2] if len(sys.argv) > 2 else '.'
        copy_examples('referencetest', destination=dest)
        copy_examples('constraints', destination=dest)
        copy_examples('rexpy', destination=dest)
    elif name in ('version', '-v', '--version'):
        pdverify.main(['tdda', '-v'])
    elif name in ('test',):
        sys.exit(os.system('%s -m tdda.testtdda' % sys.executable) != 0)
    elif name in ('help', '-h', '-?', '--help'):
        print(HELP)
    else:
        print(HELP, file=sys.stderr)
        sys.exit(1)

