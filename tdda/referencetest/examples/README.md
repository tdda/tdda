# Examples of using tdda.refererencetest.

**If you have a source distribution of the tdda library (typically cloned
from Github), you should first copy the directory containing this README
file to somewhere else so that you do not modify the original.**


Scenario:

    You have a python module called `generators.py`, which is responsible
    for generating some two different HTML pages. (You can look at these
    in `reference/file_result.html` and `reference/string_result.html`.)

    Testing that it's generated the correct HTML isn't hugely easy just
    using the standard unit-testing tools on their own. You're continually
    making updates to the generator code, and some of these updates will
    change the output in ways that don't really matter; updating version
    numbers, etc, shouldn't cause tests to stop working, but other changes
    do need to be checked.


This directory contains the generators.py file, and two test modules
--- one using the standard unittest framework, and the other using the
www.pytest.org pytest framework.


Step 1:

    Run the tests using the initial unmodified version of generators.py.

    That's either:

        python unittest/test_using_referencetestcase.py

    or:

        cd pytest
        pytest
        cd ..

    The tests should pass. (There are two of them.)

Step 2:

    Make a one or more changes to the generation code in the generate_string
    function in `generators.py` to change the HTML output.
    Specifically, try changing the title in <h1> ... </h1>
    in some way (e.g. to upper case) in the generate_string function..

    The test should then fail and suggest a diff command to run
    to see the difference.

    Rerun with

        python test_using_referencetestcase.py -W

    or:

        pytest pytest/test_using_referencepytest.py --W

    and it will re-write the reference output to match your modified
    results. The files in the `reference` subdirectory will have changed
    to reflect your changes to the generators.

    Running the tests should now pass again.

Step 3:

    Make a non-substantive change (such as changing the version numbers)
    in generators.py, and run the tests again (without the -W option; you're
    wanting to just run  the tests, not regenenerate the expected results).

    They should all still pass.

