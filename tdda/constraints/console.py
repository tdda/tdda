# -*- coding: utf-8 -*-

"""
Command line interface for constraint discovery and verification.

If pandas is available, constraints can be discovered and verified on
.csv files and saved .parquet dataframe files.

If supported database drivers are available, constraints can be discovered
and verified on tables in databases.

Constraint discovery and verification may be available for other data
sources too, via any extensions specified in the `TDDA_EXTENSIONS`
environment variable, if these are loadable using the normal Python module
loading rules.
"""

import importlib
import os
import sys
import unittest

from tdda.examples import copy_examples
from tdda.constraints.base import Marks
from tdda.constraints.pd.discover import pd_discover_parser
from tdda.constraints.pd.verify import pd_verify_parser
from tdda.constraints.pd.detect import pd_detect_parser
from tdda.referencetest.gentest import gentest_wrapper

from tdda import __version__


HELP="""Use
    tdda discover      to perform constraint discovery
    tdda verify        to verify data against constraints
    tdda detect        to detect failed constraints on data
    tdda examples      to copy the example data and code
    tdda gentest       to generate a reference test "automagically" (BETA)
    tdda version       to print the TDDA version number
    tdda help          to print this help
    tdda help COMMAND  to print help on COMMAND (discover, verify or detect)
    tdda test          to run the tdda library's tests.
    tdda diff a b      to compare two parquet or CSV files (EXPERIMENTAL)"""


STANDARD_EXTENSIONS = [
    'tdda.constraints.pd.extension.TDDAPandasExtension',
    'tdda.constraints.db.extension.TDDADatabaseExtension',
]


def help(extensions, cmd=None, stream=sys.stdout):
    if cmd:
        if cmd in ('discover', 'verify', 'detect'):
            # display detailed help for discover, verify or detect.
            # note that we use the Pandas variant to show the details, but
            # we also list the various input sources for all of the other
            # extensions (like databases), as providing the full detail
            # for everything would probably not be very helpful,
            print(file=stream)
            if cmd == 'discover':
                pd_discover_parser().print_help(stream)
            elif cmd == 'verify':
                pd_verify_parser().print_help(stream)
            elif cmd == 'detect':
                pd_detect_parser().print_help(stream)
            print('\n%s is available for the following:'
                  % cmd.title(), file=stream)
            for ext in extensions:
                ext.help(stream)
            print(file=stream)
        elif cmd == 'examples':
            print('\ntdda examples [module] [directory]\n\n'
                  'Write out example code and data for a particular module '
                  '(referencetest,\nconstraints or rexpy), to the specified '
                  'directory.\n'
                  '\nIf no module is specified, examples for all three are '
                  'written out.\n'
                  '\nIf no output directory is specified, the examples are '
                  'written to a subdirectory\nof the current directory.\n'
                  '\nTo write out all of the examples for all three modules to '
                  'subdirectories\nwithin the current directory, just use:\n'
                  '    tdda examples\n', file=stream)
        elif cmd == 'gentest':
            print('\ntdda gentest  -- to run the wizard\n'
                  'tdda gentest \'quoted shell command\' test_outputfile.py '
                  '[reference files]\n', file=stream)
        elif cmd == 'diff':
            print(
                '\ntdda diff a b  -- compare csv or parquet files a and b.\n\n'
                'This is experimental functionality.\n'
                'Currently, it will always show summary differences, but\n'
                'will only should differences in values if the data frames\n'
                'that results from loading the files have the same structure\n'
                '(number of rows and columns, column names, loose column '
                'types).\n'
                '[reference files]\n', file=stream)
        else:
            print('\nNo help available for %s. Try one of the following:\n'
                  '    tdda help discover\n'
                  '    tdda help verify\n'
                  '    tdda help detect\n'
                  '    tdda help examples\n' % cmd)
    else:
        print(HELP, file=stream)
        print(file=stream)
        print('Constraint discovery and verification is available for:\n',
            file=stream)
        for ext in extensions:
            ext.help(stream=stream)
            print(file=stream)
        print('Use "tdda help COMMAND" to get more detailed help about '
              'a particular command.\nE.g. "tdda help verify"\n',
              file=stream)
    if os.name == 'nt' or True:
        print('If this tick (%s) and cross (%s) are not being displayed '
              'correctly, you probably\nneed to use a different font, '
              'or use --ascii.\n'
              % (Marks.tick, Marks.cross))


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
    except ImportError as e:
        print('Warning: no tdda constraint module %s (%s)'
              % (modulename, str(e)), file=sys.stderr)
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


def no_constraints(name, msg, argv, extensions):
    """
    When no constraint discovery or verification could be done, show
    some help about it.
    """
    inputs = [a for a in argv
                if not a.startswith('-') and not a.endswith('.tdda')]
    if inputs:
        print('%s for %s' % (msg, ' '.join(inputs)), file=sys.stderr)
    help(extensions, name, stream=sys.stderr)


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
        no_constraints(name, 'No discovery available', argv[2:], extensions)
    elif name == 'verify':
        for ext in extensions:
            if ext.applicable():
                return ext.verify()
        no_constraints(name, 'No verification available', argv[2:], extensions)
    elif name == 'detect':
        for ext in extensions:
            if ext.applicable():
                return ext.detect()
        no_constraints(name, 'No detection available', argv[2:], extensions)
    elif name == 'examples':
        item = argv[2] if len(argv) > 2 else '.'
        if item in ('referencetest', 'constraints', 'rexpy', 'gentest'):
            dest = argv[3] if len(argv) > 3 else '.'
            copy_examples(item, destination=dest, verbose=verbose)
        else:
            dest = argv[2] if len(argv) > 2 else '.'
            for item in ('referencetest', 'constraints', 'rexpy', 'gentest'):
                copy_examples(item, destination=dest, verbose=verbose)
    elif name == 'gentest':
        gentest_wrapper(argv[2:])
    elif name in ('version', '-v', '--version'):
        print(__version__)
    elif name == 'test':
        from tdda import testtdda
        testtdda.testall(module=testtdda, argv=['python'])
    elif name == 'diff':
        from tdda.referencetest.ddiff import ddiff_helper
        ddiff_helper(argv[2:])
    elif name in ('help', '-h', '-?', '--help'):
        cmd = sys.argv[2] if len(sys.argv) > 2 else None
        help(extensions, cmd, stream=sys.stderr)
    else:
        help(extensions, stream=sys.stderr)
        sys.exit(1)


def main():
    main_with_argv(sys.argv)


if __name__ == '__main__':
    main()
