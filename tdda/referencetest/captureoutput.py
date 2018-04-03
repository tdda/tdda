# -*- coding: utf-8 -*-
"""
captureoutput.py: CaptureOutput
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import sys


class CaptureOutput(object):
    """
    Class for capturing a stream (typically) stdout.

    Typical Usage:

        c = CaptureOutput()  # for stdout; add stream='stderr' for stderr.
        <do stuff>
        c.restore()
        printed = str(c)
    """
    def __init__(self, echo=False, stream='stdout'):
        self.stream = stream
        if stream == 'stdout':
            self.saved = sys.stdout
            sys.stdout = self
        elif stream == 'stderr':
            self.saved = sys.stderr
            sys.stderr = self
        else:
            raise Exception('Unsupported capture stream %s' % stream)
        self.out = []
        self.echo = echo

    def write(self, s):
        self.out.append(s)
        if self.echo:
            self.saved.write(s)

    def flush(self):
        if self.echo:
            self.saved.flush()

    def restore(self):
        if self.stream == 'stdout':
            sys.stdout = self.saved
        else:
            sys.stderr = self.saved

    def __str__(self):
        return ''.join(self.out)


