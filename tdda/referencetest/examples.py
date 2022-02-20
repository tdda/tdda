# -*- coding: utf-8 -*-
"""
The :py:mod:`tdda.referencetest` module includes a set of examples,
for both :py:mod:`unittest` and :py:mod:`pytest`.

To copy these examples, run the command::

    tdda examples referencetest [directory]

If ``directory`` is not supplied ``referencetest-examples`` will be used.

Alternatively, you can copy all examples using the following command::

    tdda examples

which will create a number of separate subdirectories.
"""

from tdda import examples

if __name__ == '__main__':
    examples.copy_main('referencetest')

