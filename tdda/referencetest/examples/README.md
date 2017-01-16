
Examples of using tdda.refererencetest.

To step through these examples, you should first take a copy of the
entire `examples` subdirectory, and put it somewhere else. You'll be
making modifications to it, to see the affect of change, and you don't
want to be modifying the originals.


Scenario:

    You have a python module called `generators.py`, which is responsible
    for generating some HTML.

    Testing that it's generated the correct HTML isn't hugely easy just
    using the standard unit-testing tools on their own. You're continually
    making updates to the generator code, and some of these updates will
    change the output in ways that don't really matter; updating version
    numbers, etc, shouldn't cause tests to stop working, but other changes
    do need to be checked.


This examples directory contains the generators.py file, and also a unit-test
module, for testing it using tdda.referencetest. In fact there are two test
modules - one using the standard unittest framework, and the other using the
www.pytest.org pytest framework.


Step 1:

    Take a *copy* of the entire examples directory, if you haven't already
    done so. All subsequent steps should be carried out in that copy, not
    in the original source.

Step 2:

    Run the tests using the initial unmodified version of generators.py.

    That's either:

        python unittest/test_using_referencetestcase.py

    or:

        pytest pytest/test_using_referencepytest.py

    The tests should all pass.

Step 3:

    Make a substantive change to the generation code in the generate_string
    function in `generators.py` to change the HTML output. See doc strings
    inside to see how to make the tests fail.

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

Step 4:

    Make a non-substantive change (such as changing the version numbers)
    in generators.py, and run the tests again (without the -W option; you're
    wanting to just run  the tests, not regenenerate the expected results).

    They should all still pass.

