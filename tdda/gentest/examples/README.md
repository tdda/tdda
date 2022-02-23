Examples for Gentest
====================

This directory contains simple examples for Gentest.

there are more complex examples, using R code as an illustration,
in the subdirectory `r-examples`.

Running the Examples
--------------------

Example 1: Hey, Cats!
~~~~~~~~~~~~~~~~~~~~~
Run

    tdda gentest 'cat hey'

which should generate a test file `test_cat_hey.py`.
This is Example 1 in the TDDA Gentest example at
<https://tdda.readthedocs.io/gentest.html#example-1-hey-cats-not-using-wizard>.

* Run the test by typing:

    python test_cat_hey.py

* If all went well, the output will be something like:

      python test_cat_hey.py
      ....
      --------------------------------------------------------------------
      Ran 4 tests in 0.137s

      OK

* You should now have a directory ref/cat_hey, which will contain two files.
  `STDOUT` should contain the output the `cat hey` produces.
  `STDERR` should be empty.


Example 2: The Gentest Wizard with a Shell Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The second example uses the Gentest wizard.
This is Example 2 in the TDDA Gentest example at
<https://tdda.readthedocs.io/gentest.html#example-2-using-the-gentest-wizard>

Invoke the wizard by just typing:

    tdda gentest

* You will be prompted for various things. Specify the command to be
  run as

      sh example2.sh

* Accept the defaults for everything else except the number of times
  to run the script, where you should enter `10`.

Gentest should generate `test_sh_example2.py`, and a new subdirectory
`sh_example2` of the `ref` directory.

In this case, whether the tests pass when you run them will depend
on timing random numbers: You may get this:


    $ python test_two.py
    .....
    ----------------------------------------------------------------------
    Ran 5 tests in 0.258s

    OK

or you may get a failure. See the documentation for more details.

