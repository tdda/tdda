"""
The ``tdda.constraints`` module includes a set of examples.

To copy these constraints examples, run the command::

    tdda examples constraints

A directory ``constraints_examples`` will be created (or overwritten)
in the current directory.

Alternatively, you can copy all examples using the following command::

    tdda examples

which will create a number of separate subdirectories.
"""

from tdda import examples

if __name__ == '__main__':
    examples.copy_main('constraints')
