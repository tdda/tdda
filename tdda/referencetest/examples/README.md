# Examples of using tdda.refererencetest.

**If you have a source distribution of the tdda library (typically cloned
from Github), you should first copy the directory containing this README
file to somewhere else so that you do not modify the original.**


## Scenario 1: Testing Text/Text-File Generation

You have a python module called `generators.py`, which is responsible
for generating some two different HTML pages. (You can look at
these in `reference/file_result.html` and
`reference/string_result.html`.)

Testing that it's generated the correct HTML isn't hugely easy just
using the standard unit-testing tools on their own. You're continually
making updates to the generator code, and some of these updates will
change the output in ways that don't really matter; updating version
numbers, etc, shouldn't cause tests to stop working, but other changes
do need to be checked.


This directory contains the generators.py file, and two test modules
--- one using the standard unittest framework, and the other using the
www.pytest.org pytest framework.


### Step 1:

Run the tests using the initial unmodified version of generators.py.

That's either:

    python unittest/test_using_referencetestcase.py

or:

    cd pytest
    pytest
    cd ..

The tests should pass. (There are five tests in total, of which two
are affected by generators.py.)

### Step 2:

Make a one or more changes to the generation code in the `generate_string`
function in `generators.py` to change the HTML output.
Specifically, try changing the title in `<h1> ... </h1>`
in some way (e.g. to upper case) in the generate_string function..

Two tests should then fail and suggest suitable diff commands to run
to see the differences.

In this scenario, we assume that the new results are the ones we now
want. So rerun with

    python test_using_referencetestcase.py -W

or:

    pytest pytest/test_using_referencepytest.py --write-all -s

and it will re-write the reference output to match your modified
results. The files in the `reference` subdirectory will have changed
to reflect your changes to the generators.

Running the tests should now pass again.


### Step 3:

In the assertions, we have specified that lines containing either
"Copyright" or "Version" should be ignored.  Make a change to the
version number in generators.py, and run the tests again (without the
`-W` or `--write-all` option, so as not to rewrite the results).
They should all still pass.


## Scenario 2: Testing DataFrames and CSV Files

You have a python module called `dataframes.py`, which is responsible
for generating some structured data---in this case a Pandas DataFrame,
though it could equally be a CSV file or similar.

In testing that the data is correct, we have various considerations
including

  - do we care about types or just values?
  - do we want exact matching of floating-point values
    or are we using some tolerance?
  - do we care about column order in the DataFrame/CSV file.

We would like options to control these and also helpful diagnostics
when there are differences (rather than just "DataFrames differ!")
The ReferenceTest methods help here.

### Step 1:

Run the tests using the initial unmodified version of dataframes.py.

That's either:

    python unittest/test_using_referencetestcase.py

or:

    cd pytest
    pytest
    cd ..

The tests should pass. (There are five tests in total, of which three
are affected by dataframes.py.)


### Step 2:

Make a one or more changes to the generation code in the `generate_dataframe`
function in `dataframes.py` to change the DataFrame generated.
One simple option is to change the default precision from 3 to (say) 2.
This will result in a different string column `s` being generated.

Three tests should then fail and suggest diff commands to run
to see the differences. It also shows you, in some detail, where the
differences are (in column `s`, if you made the suggested change).

Note that the test `testExampleMultipleCSVGeneration` checks two
CSV files, both of which have differences, and that both sets of
differences are highlighted.

We assume that these new (precision 2) results are the ones we want.
So rerun with

    python test_using_referencetestcase.py -W

or:

    pytest pytest/test_using_referencepytest.py --write-all -s

and it will re-write the reference output to match your modified
results. The files in the `reference` subdirectory will have changed
to reflect your changes to the generators.

Running the tests should now pass again.

### Step 3:

In the assertions for these cases, we have specified that content
the `random` column should be ignored. So you could also completely
change its generation to be something more like:

        df['random'] = [1] * nrows

and rerun the tests (without the re-write flags, `-W` / `--write-all`).

They should all still pass.

