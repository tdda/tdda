# -*- coding: utf-8 -*-
"""
TDDA rexpy is supplied with a set of examples.

To copy the rexpy examples, run the command::

    tdda examples rexpy

This will create or overwrite a directory ``rexpy_examples``
in the current directory.

Alternatively, you can copy all examples using the following command::

    tdda examples

which will create a number of separate subdirectories.
"""

from tdda import examples

if __name__ == '__main__':
    examples.copy_main('rexpy')
