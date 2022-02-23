R Examples for Gentest
======================

Code and Data
-------------

These scripts and datasets are closely based on examples provided by
the United States Environmental Protection Agency data at
<https://www.epa.gov/caddis-vol4/download-r-scripts-and-sample-data>

In order to use them, you need a functioning installation of R
that can be invoked with the command `Rscript`.
R also needs to have the packages `gam` and `bio.infer` installed.
Those can be installed using the script `00-install-packages.R`.

The scripts have been:
* renamed with numbers to indicate the order in which to run them
* modified to run the setup scripts `0-set-variables.R`, required
  for them to work
* Scripts 3 and 4 have been modifed to write the plots they produce
  to PostScript files.


Running the Examples
--------------------

R EXAMPLE 1: EPA Weighted Averages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    tdda gentest 'Rscript 1-compute-weighted-average-tolerance-values.R' one

* This generates a test for running the script
  `1-compute-weighted-average-tolerance-values.R`,
  This script computes weighted average tolerances for three taxas
  and prints them to the screen.

* The 'one' is a shorter name to use for the test script.
  If we don't specify it, a rather long filename, based on a
  sanitized version of the command, will be used.
  (We could have specified `test_one.py` too, but `one` is enough.)

* The script should generate four tests in `test_one.py`.

* Run the test by typing:

    python test_one.py

  This assumes that the command `python` runs a suitable Python 3
  with access to the TDDA library. Replace `python` with `python3`
  or whatever you need to run the tests under a target version on python

* If all went well, the output will be something like:

      python test_one.py
      ....
      ----------------------------------------------------------------------
      Ran 4 tests in 0.237s

      OK

* You should now have a directory `ref/one`, which will contain two files.
  STDOUT should contain the output that R produces to the screen, which
  includes a lot of startup chatter, the commands it ran, and the output.


R EXAMPLE 2: A PDF Plot
~~~~~~~~~~~~~~~~~~~~~~~

The second script from the EPA generates a triptych of graphs.
The code on the website displays the graphs as a pop-up, but we've
modifed the code to write the graphs out as a PDF, which is rather
easier to test.

To run the second example, you can either follow a similar receipe to
the last, typing

    tdda gentest 'Rscript 2-compute-cumulative-percentiles.R' two

or use Genest's wizard, by just typing:

    tdda gentest

* At the first prompt put in the command to run the second script:

    Enter name for test script [test_Rscript_2_compute_cumulative_percentiles_R]: two

* Accept the deafiults for everything else, just hitting the `RETURN` (enter)
  key until it stops

Gentest should generate `test_two.py`, and a new subdirectory `two` of the
`ref` directory.

In this case, whether the tasts pass when you run them will depend on timing
and luck: You may get this:


    $ python test_two.py
    .....
    ----------------------------------------------------------------------
    Ran 5 tests in 0.258s

    OK

or you may get something more like:

    $ python test_two.py 
    ..2 lines are different, starting at line 5
    Compare with:
        diff /home/tdda/tmp/gentest_examples/r-examples/plots2.pdf /home/tdda/tmp/gentest_examples/r-examples/ref/two/plots2.pdf

    F..
    ======================================================================
    FAIL: test_plots2_pdf (__main__.Test)
    ----------------------------------------------------------------------
    Traceback (most recent call last):
      File "/home/tdda/tmp/gentest_examples/r-examples/test_two.py", line 52, in test_plots2_pdf
        self.assertFileCorrect(os.path.join(self.cwd, 'plots2.pdf'),
    AssertionError: False is not true : 2 lines are different, starting at line 5
    Compare with:
        diff /home/tdda/tmp/gentest_examples/r-examples/plots2.pdf /home/tdda/tmp/gentest_examples/r-examples/ref/two/plots2.pdf


    ----------------------------------------------------------------------
    Ran 5 tests in 0.288s

    FAILED (failures=1)

The reason it may pass or fail is that R's PDF writer write a timestamp
into the PDF file, accurate to the second. If the timing is such that the
timestamp the same, to the second, for each of the two trial runs
Gentest does by default, it will see two identical PDF files and assume
they're always the same. But by the time you run the test, the time
will almost certainly be later, and a slightly different PDF will be generated.

In the in which the trial PDFs were identical, the test code Gentest
will generate for write the PDF file will look something like this:

    def test_plots2_pdf(self):
        self.assertFileCorrect(os.path.join(self.cwd, 'plots2.pdf'),
                               os.path.join(self.refdir, 'plots2.pdf'))


If, however, the PDF generation happened at different times during Gentest's,
trial runs, it will see different PDFs and generate a better test:

    def test_plots2_pdf(self):
        patterns = [
            r'^/[A-Z][a-z]+[A-Z][a-z]{3} \(D:[0-9]{14}\)$',
        ]
        self.assertFileCorrect(os.path.join(self.cwd, 'plots2.pdf'),
                               os.path.join(self.refdir, 'plots2.pdf'),
                               ignore_patterns=patterns)

It can be hard to see, because PDFs are technically binary files, though
the often mostly consist of text and can be treated more-or-less like text
if you are careful. In fact, the sort of thing they contain is this:

    /CreationDate (D:20220220134310)
    /ModDate (D:20220220134310)

Fairly obviously these are date stamps: `2022-20-22T12:43:10`, written as a
14-digit string.

In the better version of the test, which Gentest generates if its trial runs
produce differing outputs, it decides to ignore lines that match the regular
expression shown, which both of these do.

* If you get this failure, you have a few options. First, Gentest suggests
  a `diff` command you can use to examine the differences.
  In fact, the diff command is quite just to say that the files are
  binary and differ. This is technically true, though some `diff` tools
  can be persuaded to show the differences anyway.
  Even if you can's see them, what you can definitely do it open the two files
  (the diff command includes their full paths) and look at them to see whether
  they look the same. Hopefully they will.

* In terms of correcting it, the simplest thing to do is to increase the
  number of times the test is run. Depending on how fast your machine is,
  the odds are that if you increase the number of runs even to 3, the first
  and last will probably run at different times (to the _second_), and if
  you increase it to 10, this will almost certainly be true.

* Alternatively, you can edit the test yourself, but this will require you
  to write one or more exclusion patterns, as Gentest did. They can, however,
  be simpler.  One possibiity is to use `ignore_substrings`, which ignores
  lines that contain the subtrings given.

    def test_plots2_pdf(self):
        ignores = [
            '/CreationDate',
            '/ModDate'
        ]
        self.assertFileCorrect(os.path.join(self.cwd, 'plots2.pdf'),
                               os.path.join(self.refdir, 'plots2.pdf'),
                               ignore_substrings=ignores)

* In future, Gentest will probably allow you to specify a time two
  wait between invocations of the test command, which would be another
  way to fix the problem.

