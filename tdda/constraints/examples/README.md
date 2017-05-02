# Examples of using tdda.constraints

## Periodic table examples ("elements" dataset)

1. Generate constraints from first 92 elements in periodic table.

       python elements_discover_92.py

   This reads data from testdata/elements92.csv,
   and writes out discovered constraints to ./elements92.tdda

2. Verify the same data against those constraints. (This, of course,
   should be successful.)

       python elements_verify_92.py

3. Now try verifying a more complete version of the periodic table
   (the first 118 elements) against the same constraints file:

       python elements_verify_118_against_92.py

   Now we get some failures. For example, the original discovered highest
   atomic number of Z=92 is not satisfied in the expanded data.

4. The example data includes elements118.tdda, a TDDA file generated from
   all 118 elements. You can verify that these constraints are satisfied
   by the larger dataset by running

       python elements_verify_118.py


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

