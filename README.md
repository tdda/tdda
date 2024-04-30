Test-Driven Data Analysis (Python TDDA library)
===============================================

What is it?
-----------

The TDDA Python module provides command-line and Python API support for
the overall process of data analysis, through the following tools:

 - **Reference Testing**: extensions to `unittest` and `pytest` for
   managing testing of data analysis pipelines, where the results are
   typically much larger, and more complex, than single numerical
   values.

 - **Constraints**: tools (and API) for discovery of constraints from data,
   for validation of constraints on new data, and for anomaly detection.

 - **Finding Regular Expressions (Rexpy)**: tools (and API) for automatically
   inferring regular expressions from text data.

 - **Automatic Test Generation (Gentest)**: TDDA can generate tests for
   more-or-less any command that can be run from a command line,
   whether it be Python code, R code, a shell script, a shell
   command, a `Makefile` or a multi-language pipeline involving
   compiled code. _"Gentest writes tests, so you don't have to."™_

<img width="100%" src="doc/source/image/tdda-machines-light.png"/>

Documentation
-------------

http://tdda.readthedocs.io

Installation
------------

The simplest way to install all of the TDDA Python modules is using *pip*:

    pip install tdda

The full set of sources, including all examples, are downloadable from
PyPi with:

    pip download --no-binary :all: tdda

The sources are also publicly available from Github:

    git clone git@github.com:tdda/tdda.git

Documentation is available at http://tdda.readthedocs.io.

If you clone the Github repo, use

    python setup.py install

afterwards to install the command-line tools (`tdda` and `rexpy`).


*Reference Tests*
-----------------

The `tdda.referencetest` library is used to support
the creation of *reference tests*, based on either unittest or pytest.

These are like other tests except:

  1. They have special support for comparing strings to files
     and files to files.
  2. That support includes the ability to provide exclusion patterns
     (for things like dates and versions that might be in the output).
  3. When a string/file assertion fails, it spits out the command you
     need to diff the output.
  4. If there were exclusion patterns, it also writes modified versions
     of both the actual and expected output and also prints the diff
     command needed to compare those.
  5. They have special support for handling CSV files.
  6. It supports flags (-w and -W)  to rewrite the reference (expected)
     results once you have confirmed that the new actuals are correct.

For more details from a source distribution or checkout, see the `README.md`
file and examples in the `referencetest` subdirectory.

*Constraints*
-------------

The `tdda.constraints` library is used to 'discover' constraints
from a (Pandas) DataFrame, write them out as JSON, and to verify that
datasets meet the constraints in the constraints file.

For more details from a source distribution or checkout, see the `README.md`
file and examples in the `constraints` subdirectory.

*Finding Regular Expressions*
-----------------------------

The `tdda` repository also includes `rexpy`, a tool for automatically
inferring regular expressions from a single field of data examples.

*Resources*
-----------

Resources on these topics include:

  * TDDA Blog: http://www.tdda.info
  * Quick Reference Guide ("Cheatsheet"): http://www.tdda.info/pdf/tdda-quickref.pdf
  * 1-page summary: https://stochasticsolutions.com/pdf/TDDA-One-Pager.pdf
  * Full documentation: http://tdda.readthedocs.io
  * General Notes on Constraints and Assertions: http://www.tdda.info/constraints-and-assertions
  * Notes on using the Pandas constraints library:
    http://www.tdda.info/constraint-discovery-and-verification-for-pandas-dataframes
  * PyCon UK Talk on TDDA:
      - Video: https://www.youtube.com/watch?v=FIw_7aUuY50
      - Slides and Rough Transcript:   http://www.tdda.info/slides-and-rough-transcript-of-tdda-talk-from-pycon-uk-2016

  * <a rel="me" href="https://mathstodon.xyz/@tdda">Mastodon</a>


All examples, tests and code run under Python 2.7, Python 3.5 and Python 3.6.

