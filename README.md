# tdda
Test-Driven Data Analysis Functions:

 * *Level 0:* `WritableTestCase` is a subclass of unittest used to support
   the creation of *referene tests*. These are like other tests except:
      1. They have special support for comparing strings to files
         and files to files
      2. That support includes the ability to provide exclusion patterns
         (for things like dates and versions that might be in the output)
      3. When a string/file assertion fails, it spits out the command you
         need to diff the output
      4. If there were exclusion patterns, it also writes modified versions
         of both the actual and expected output and also prints the diff
         command needed to compare those
      5. It supports a -W flag to rewrite the reference (expected) result
         once you have confirmed that the new actual is correct.

 * *Level 1:* the `constraints` library is used to 'discover' constraints
   from a (pandas) DataFrame, write them out as JSON, and to verify that
   datasets meet the constraints in the constraints file. See the README
   in the `constraints` subdirectory for usage details.

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


Explanatory examples of how to use `writabletestcase` are in the `examples`
subdirectory.

Use

    cd examples
    python test_using_writabletestcase.py

to run an example test.

See doc strings inside to see how to make the tests fail, then re-write
the output.

Briefly: edit the generation functions in `examples/generators.py`
to generate different output, re-run the tests, see them fail, check
the output and then run

    python test_using_writabletestcase.py -w

to re-write the reference output in `examples/reference`,

after which if you run again with

    python test_using_writabletestcase.py

Test tests should pass again.

Obviously, you should only rewrite the test output after carefully verifying
the the changes are OK!

All examples, tests and code should run under Python2 and Python3.
