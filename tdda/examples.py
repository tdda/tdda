# -*- coding: utf-8 -*-

"""
examples.py: copy example files to a specified directory

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2017
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import shutil
import sys


def copy_examples(name, destination='.', verbose=True):
    """
    Copy example files to a specified directory
    """
    path = os.path.join(os.path.dirname(__file__), name)
    srcdir = os.path.join(path, 'examples')
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
        elif name.endswith('.pyc'):
            continue
        else:
            binary = 'b' if fullname.endswith('.feather') else ''
            with open(fullname, 'r%s' % binary) as fin:
                with open(os.path.join(destination, name),
                                       'w%s' % binary) as fout:
                    fout.write(fin.read())


def copy_main(name, verbose=True):
    if len(sys.argv) > 2:
        print('USAGE: examples [destination-directory]', file=sys.stderr)
        sys.exit(1)
    destination = sys.argv[1] if len(sys.argv) == 2 else '.'
    copy_examples(name, destination, verbose=verbose)

