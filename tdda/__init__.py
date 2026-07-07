"""
Test-Driven Data Analysis (Python TDDA library)
===============================================

The tdda package provides Python support for test-driven data analysis.

The tdda.referencetest library is used to support the creation of
reference tests, based on either unittest or pytest.

For usage details:

    >>> from tdda import referencetest
    >>> help(referencetest)


The tdda.constraints library is used to 'discover' constraints
from a (Pandas) DataFrame, write them out as JSON, and to verify that
datasets meet the constraints in the constraints file.

For usage details:

    >>> from tdda import constraints
    >>> help(constraints)


The tdda package also includes rexpy, a tool for automatically
inferring regular expressions from a single field of data examples.

For usage details:

    >>> from tdda import rexpy
    >>> help(rexpy)


tdda.rexpy also includes Xerpy, which generates example strings
matching a regular expression -- the inverse of rexpy's own
inference.

For usage details:

    >>> from tdda.rexpy import Xerpy
    >>> help(Xerpy)

"""

import sys

if sys.platform == 'win32':
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

from tdda.version import version as __version__
from . import referencetest
from . import constraints
from . import rexpy
