# -*- coding: utf-8 -*-

"""
examples.py: copy example files to a specified directory

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2022
"""

import os
import shutil
import sys
import zipfile


def examples_srcdir(name):
    path = os.path.join(os.path.dirname(__file__), name)
    return os.path.join(path, 'examples')


def copy_examples(name, destination='.', verbose=True):
    """
    Copy example files to a specified directory
    """
    srcdir = examples_srcdir(name)
    if not os.path.isdir(destination):
        print('copyexamples: output directory %s does not exist' % destination,
              file=sys.stderr)
        sys.exit(1)
    outdir = os.path.join(destination, '%s_examples' % name)
    shutil.rmtree(outdir, ignore_errors=True)
    os.mkdir(outdir)
    copy(srcdir, outdir)
    if verbose:
        print('Copied example files for tdda.%s to %s' % (name, outdir))


def copy(srcdir, destination):
    """
    Recursive copy
    """
    for name in os.listdir(srcdir):
        fullname = os.path.join(srcdir, name)
        if os.path.isdir(fullname):
            if name in ('.cache', '__pycache__'):
                continue
            outdir = os.path.join(destination, name)
            if not os.path.exists(outdir):
                os.mkdir(outdir)
            copy(fullname, outdir)
        elif name.endswith('.pyc') or name.endswith('~'):
            continue
        elif name == ('accounts.zip'):
            copy_accounts_data_unzipped(destination)
        else:
            for run in (0, 1):
                binary = 'b' if run  or fullname.endswith('.feather') else ''
                try:
                    with open(fullname, 'r%s' % binary) as fin:
                        with open(os.path.join(destination, name),
                                               'w%s' % binary) as fout:
                            fout.write(fin.read())
                    break
                except UnicodeDecodeError:
                    if run:
                        raise


def copy_accounts_data_unzipped(destdir):
    srcdir = os.path.join(examples_srcdir('constraints'), 'testdata')
    zippath = os.path.join(srcdir, 'accounts.zip')
    with zipfile.ZipFile(zippath) as z:
        for f in z.namelist():
            z.extract(f, destdir)


def copy_main(name, verbose=True):
    if len(sys.argv) > 2:
        print('USAGE: examples [destination-directory]', file=sys.stderr)
        sys.exit(1)
    destination = sys.argv[1] if len(sys.argv) == 2 else '.'
    copy_examples(name, destination, verbose=verbose)
