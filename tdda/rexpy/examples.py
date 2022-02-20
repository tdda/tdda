# -*- coding: utf-8 -*-
"""
TDDA rexpy is supplied with a set of examples.

To copy the rexpy examples, run the command::

    tdda examples rexpy [directory]

If ``directory`` is not supplied, ``rexpy_examples`` will be used.

Alternatively, you can copy all examples using the following command::

    tdda examples

which will create a number of separate subdirectories.
"""
from tdda import examples

if __name__ == '__main__':
    examples.copy_main('rexpy')

