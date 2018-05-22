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

"""
__version__ = '1.0.01'
