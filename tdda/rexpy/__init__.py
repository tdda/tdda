"""
rexpy: Easier regular expression generation

Rexpy infers regular expressions on a line-by-line basis from text data
examples.

To run the rexpy tool:

    python -m tdda.rexpy.rexpy [inputfile]

For details, including API use:

    >>> from tdda.rexpy import rexpy
    >>> help(rexpy)

To copy the examples to your own 'rexpy-examples' directory:

    python -m tdda.rexpy.examples [mydirectory]

"""

from tdda.rexpy.rexpy import *
