# Examples of using tdda.constraints with CSV files

## Command-line Periodic table examples ("elements" dataset)

1. Generate constraints from first 92 elements in periodic table.

       tdda discover testdata/elements92.csv elements92.tdda

   This reads data from testdata/elements92.csv,
   and writes out discovered constraints to ./elements92.tdda

2. Verify the same data against those constraints. (This, of course,
   should be successful.)

       tdda verify testdata/elements92.csv elements92.tdda

3. Now try verifying a more complete version of the periodic table
   (the first 118 elements) against the same constraints file:

       tdda verify testdata/elements118.csv elements92.tdda

   Now we get some failures. For example, the original discovered highest
   atomic number of Z=92 is not satisfied in the expanded data.

4. The example data includes elements118.tdda, a TDDA file generated from
   all 118 elements. You can verify that these constraints are satisfied
   by the larger dataset by running

       tdda verify testdata/elements118.csv elements118.tdda


## Python API Periodic table examples ("elements" dataset)

For embedding constraint discovery and verification within a Python
environment, Python API examples are provided which carry out the same
steps as the command-line example steps above, but with each step
explicitly implemented using custom Python code, using the API.

The steps here are equivalent to steps 1 to 4 using the 'tdda' command
above:

1.  python elements_discover_92.py
2.  python elements_verify_92.py
3.  python elements_verify_118_against_92.py
4.  python elements_verify_118.py


## Creating DataFrame Output from Verifications

The elements examples just generate textual output with ticks and crosses
for each constraint for each field and a summary of the total number of
passes and failures.

It is also possible to generate a Pandas DataFrame containing the pass/fail
information. This is done in the "simple" examples below:

1. Run

       python simple_discovery.py

to generate a TDDA file (./example_constraints.tdda) for the following,
tiny, generated dataset:

           a    b
        0  1  one
        1  2  two
        2  9  NaN

2. Verify a smaller, DataFrame that is consistent with the constraints,
   namely:

           a    b
        0  2  one
        1  4  NaN

   by running:

       python simple_verify_pass.py

   This shows the same textual summary of passes and failures, but also
   generates and displays a DataFrame with one row per field (i.e., one for
   Field a and another for Field b) and a column for each constraint.
   The values in the DataFrame are

      True: if the constraint existed and was satisfied
      False: if the constraint exists and was not satisified
      NaN: if that constraint was not generated for that field

   (There are also columns for numbers of passes and failures.)

3. Now repeat the exervise with another small, DataFrame that is not consistent
   with many of the generated constraints, namely:

              a      b
        0   0.0    one
        1   1.0    one
        2   2.0    two
        3  10.0  three
        4   NaN    NaN

   Test this by running

       python simple_verify_fail.py

   There should be 5 passes and 7 failures.


# Example of extending the tdda.constraints module

The "files_extension.py" file contains Python source code for a very simple
implementation of a (not very realistic or useful) extension to the
tdda.constraints module.

The extension provides the ability to do constraint discovery and
verification on directory/folder filesystem structure (the names and
sizes of files).

To enable this extension, add the following to your environment.

For Linux, MacOS and other Unix systems:

    export TDDA_EXTENSIONS=files_extension.TDDAFilesExtension
    export PYTHONPATH=.:$PYTHONPATH

For Microsoft Windows:

    set TDDA_EXTENSIONS=files_extension.TDDAFilesExtension
    set PYTHONPATH=.;%PYTHONPATH%

Then you can discover constraints on all the example files in this directory
with:

1. Discover constraints on the files in the current directory:

        tdda discover . files.tdda

This should produce a set of constraints on the names and sizes of the files
in this directory, and write these to the file files.tdda.

2. Verify those constraints.

        tdda verify . files.tdda

   There should be a 'values' failure, because the list of files in the
   current directory now includes "files.tdda", which didn't exist at the
   point when the initial discovery was done.

3. Move files.tdda to somewhere else (such as /tmp), and rerun the
   verification:

        mv files.tdda /tmp/files.tdda
        tdda verify . /tmp/files.tdda

   Now all the constraints should all pass.

4. Create a new file that doesn't match all of those constraints (e.g. one
   with a name that is longer than any of the existing names):

        tdda verify . files.tdda

   Now several constraints should fail.

