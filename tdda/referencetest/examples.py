# -*- coding: utf-8 -*-
"""
The :py:mod:`tdda.referencetest` module includes a set of examples,
for both :py:mod:`unittest` and :py:mod:`pytest`.

To copy these examples to your own *referencetest-examples* subdirectory
(or to a location of your choice)::

    python -m tdda.referencetest.examples [mydirectory]

"""
from __future__ import absolute_import

from tdda import examples

if __name__ == '__main__':
    examples.copy_main('referencetest')

