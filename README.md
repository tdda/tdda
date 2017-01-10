# tdda
Test-Driven Data Analysis Functions:

*Level 0:*
----------

The `tdda.referencetest` library is used to support
the creation of *reference tests*, based on either unittest or pytest.
These are like other tests except:

  1. They have special support for comparing strings to files
     and files to files
  2. That support includes the ability to provide exclusion patterns
     (for things like dates and versions that might be in the output)
  3. When a string/file assertion fails, it spits out the command you
     need to diff the output
  4. If there were exclusion patterns, it also writes modified versions
     of both the actual and expected output and also prints the diff
     command needed to compare those
  5. They have special support for handling CSV files.
  6. It supports flags (-w and -W)  to rewrite the reference (expected)
     results once you have confirmed that the new actuals are correct.

See the `README.md` file in the `referencetest` subdirectory for usage details.

*Level 1:*
----------
The `tdda.constraints` library is used to 'discover' constraints
from a (pandas) DataFrame, write them out as JSON, and to verify that
datasets meet the constraints in the constraints file.

See the `README.md` file in the `constraints` subdirectory for usage details.

*Resources*
-----------

Resources on these topics include:

  * TDDA Blog: http//www.tdda.info
  * Notes on WritableTestCase:
    http://tdda.info/writabletestcase-example-use
  * General Notes on Constraints and Assertions
  * Notes on using the Pandas constraints library:
    http://www.tdda.info/constraint-discovery-and-verification-for-pandas-dataframes
  * PyCon UK Talk on TDDA:
      - Video: https://www.youtube.com/watch?v=FIw_7aUuY50
      - Slides and Rough Transcript:   http://www.tdda.info/slides-and-rough-transcript-of-tdda-talk-from-pycon-uk-2016

The `tdda` repository also includes `rexpy`, a tool for automatically
inferring regular expressions from data examples.

All examples, tests and code should run under Python2 and Python3.
