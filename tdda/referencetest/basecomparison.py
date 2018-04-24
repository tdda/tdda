# -*- coding: utf-8 -*-

"""
checkfiles.py: comparison mechanism for text files

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2018
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
# from __future__ import unicode_literals

import os
import re
import sys
import tempfile


class BaseComparison(object):

    def __init__(self, print_fn=None, verbose=True, tmp_dir=None):
        """
        Constructor for an instance of the PandasComparison class.

        The optional print_fn parameter is a function to be used to
        display information while comparison operations are running.
        If specified, it should be a function with the same signature
        as python's builtin (__future__) print function.
        """
        self.print_fn = print_fn
        self.verbose = verbose
        self.tmp_dir = tmp_dir or tempfile.gettempdir()

    def info(self, msgs, s):
        """
        Add an item to the list of messages, and also display it immediately
        if verbose is set.
        """
        msgs.append(s)
        if self.verbose and self.print_fn:
            self.print_fn(s)

    @staticmethod
    def compare_with(actual, expected, qualifier=None):
        qualifier = '' if not qualifier else (qualifier + ' ')
        if os.path.exists(expected):
            msg = 'Compare %swith:\n    %s %s %s\n'
            cmd = diffcmd()
        else:
            msg = 'Initialize %sfrom actual content with:\n    %s %s %s'
            cmd = copycmd()
        return msg % (qualifier, cmd, actual, expected)


def diffcmd():
    return 'fc' if os.name and os.name != 'posix' else 'diff'


def copycmd():
    return 'copy' if os.name and os.name != 'posix' else 'cp'

