# -*- coding: utf-8 -*-

"""
Command line interface for constraint discovery and verification.

If pandas is available, constraints can be discovered and verified on
.csv files and saved .feather dataframe files.

If supported database drivers are available, constraints can be discovered
and verified on tables in databases.

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

from tdda.examples import copy_examples
from tdda import __version__


HELP="""Use
    tdda discover  to perform constraint discovery
    tdda verify    to verify data against constraints
    tdda examples  to copy the example data and code
    tdda version   to print the TDDA version number
    tdda help      to print this help
    tdda test      to run the tdda library's tests."""


STANDARD_EXTENSIONS = [
    'tdda.constraints.pd.extension.TDDAPandasExtension',
    'tdda.constraints.db.extension.TDDADatabaseExtension',
]


def help(extensions, stream=sys.stdout):
    print(HELP, file=stream)
    print(file=stream)
    print('Constraint discovery and verification is available for:\n',
          file=stream)
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
    try:
        mod = importlib.import_module(modulename)
        return getattr(mod, classname, None)
    except ImportError:
        print('Warning: no tdda constraint module %s' % modulename,
              file=sys.stderr)
        return None


def load_all_extensions(argv, verbose=False):
    """
    Load all extensions specified via the TDDA_EXTENSIONS environment variable,
    and then load all the standard extensions.
    """
    extension_class_names = []
    if 'TDDA_EXTENSIONS' in os.environ:
        extension_class_names.extend(os.environ['TDDA_EXTENSIONS'].split(':'))
    extension_class_names.extend(STANDARD_EXTENSIONS)
    extension_classes = [load_extension(e) for e in extension_class_names]
    return [e(argv, verbose=verbose) for e in extension_classes if e]


def no_constraints(msg, argv, extensions):
    """
    When no constraint discovery or verification could be done, show
    some help about it.
    """
    inputs = [a for a in argv
                if not a.startswith('-') and not a.endswith('.tdda')]
    if inputs:
        print('%s for %s' % (msg, ' '.join(inputs)), file=sys.stderr)
    else:
        print('No data specified\n', file=sys.stderr)
        print('Input data should be specifed as one of:\n', file=sys.stderr)
        for ext in extensions:
            print('  * ' + ext.spec(), file=sys.stderr)
    print(file=sys.stderr)
    print('For more detailed help on how to specify a data source, pass in\n'
          'appropriate parameters for one of the above, and add --help.',
          file=sys.stderr)


def main_with_argv(argv, verbose=True):
    extensions = load_all_extensions(argv[1:], verbose=verbose)

    if len(argv) == 1:
        help(extensions, stream=sys.stderr)
        sys.exit(1)
    name = argv[1]

    if name in ('discover', 'disco'):
        for ext in extensions:
            if ext.applicable():
                return ext.discover()
        no_constraints('No discovery available', argv[2:], extensions)
    elif name == 'verify':
        for ext in extensions:
            if ext.applicable():
                return ext.verify()
        no_constraints('No verification available', argv[2:], extensions)
    elif name == 'examples':
        item = argv[2] if len(argv) > 2 else '.'
        if item in ('referencetest', 'constraints', 'rexpy'):
            dest = argv[3] if len(argv) > 3 else '.'
            copy_examples(item, destination=dest, verbose=verbose)
        else:
            dest = argv[2] if len(argv) > 2 else '.'
            for item in ('referencetest', 'constraints', 'rexpy'):
                copy_examples(item, destination=dest, verbose=verbose)
    elif name in ('version', '-v', '--version'):
        print(__version__)
    elif name == 'test':
        sys.exit(os.system('%s -m tdda.testtdda' % sys.executable) != 0)
    elif name in ('help', '-h', '-?', '--help'):
        help(extensions)
    else:
        help(extensions, stream=sys.stderr)
        sys.exit(1)


def main():
    main_with_argv(sys.argv)


if __name__ == '__main__':
    main()

