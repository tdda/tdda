# -*- coding: utf-8 -*-

"""
Base class for extensions.
"""

import sys


class ExtensionBase:
    def __init__(self, argv):
        self.argv = argv

    def applicable(self):
        return False

    def help(self, stream=sys.stdout):
        pass

