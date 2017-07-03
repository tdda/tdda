# -*- coding: utf-8 -*-

"""
Command line interface for constraint discovery and verification.

If pandas is available, constraints can be discovered and verified on
.csv files and saved .feather dataframe files.

Constraint discovery and verification may be available for other data
sources too, via any extensions specified in the `TDDA_EXTENSIONS`
environment variable, if these are loadable using the normal Python module
loading rules.
"""

from __future__ import print_function

import importlib
import os
import sys
import unittest

try:
    from tdda.constraints import pddiscover, pdverify
except ImportError:
    # no pandas support
    pddiscover = None
    pdverify = None

from tdda.examples import copy_examples


HELP="""Use
    tdda discover  to perform constraint discovery
    tdda verify    to verify data against constraints
    tdda examples  to copy the example data and code
    tdda version   to print the TDDA version number
    tdda help      to print this help
    tdda test      to run the tdda library's tests."""


def help(extensions, stream=sys.stdout):
    print(HELP, file=stream)
    print(file=stream)
    if pddiscover:
        print('Constraint discovery and verification is available for CSV\n'
              'files, and for Pandas and R DataFrames saved as .feather\n'
              'files.', file=stream)
    if extensions:
        print('Constraint discovery is also available for the following, via\n'
              'extension modules:\n', file=stream)
        for ext in extensions:
            ext.help(stream=stream)
            print(file=stream)


def load_extension(ext):
    """
    Dynamically load an extension class, which must be available
    using the normal module loading rules. i.e., needs to be already
    availble via sys.path (through $PYTHONPATH, or otherwise).
    """
    components = ext.split('.')
    classname = components[-1]
    modulename = '.'.join(components[:-1])
    mod = importlib.import_module(modulename)
    return getattr(mod, classname, None)


def load_all_extensions(argv):
    """
    Load all extensions specified via the TDDA_EXTENSIONS environment variable.
    """
    if 'TDDA_EXTENSIONS' in os.environ:
        extension_class_names = os.environ['TDDA_EXTENSIONS'].split(':')
        extension_classes = [load_extension(e) for e in extension_class_names]
        return [e(argv) for e in extension_classes if e]
    else:
        return []


def main():
    extensions = load_all_extensions(sys.argv[1:])

    if len(sys.argv) == 1:
        help(extensions, stream=sys.stderr)
        sys.exit(1)
    name = sys.argv[1]

    if name in ('discover', 'disco'):
        for ext in extensions:
            if ext.applicable():
                return ext.discover()
        if pddiscover:
            return pddiscover.main(sys.argv[1:])
        print('No discovery available', file=sys.stderr)
    elif name in ('verify',):
        for ext in extensions:
            if ext.applicable():
                return ext.verify()
        if pdverify:
            return pdverify.main(sys.argv[1:])
        print('No verification available', file=sys.stderr)
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
        help(extensions)
    else:
        help(extensions, stream=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

