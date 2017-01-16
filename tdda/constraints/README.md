# tdda.constraints:

Constraint generation and verification for datasets, including
Pandas DataFrames.

All examples, tests and code should run under Python2 and Python3.

See examples directory for example usage.

In particular see:

    tdda/constraints/examples/simple_generation.py

for an example of generating constraints as a .tdda JSON file, and

    tdda/constraints/examples/simple_verification.py

for an example of verifying (both satisfying and non-statisfying)
dataframes against constraints.

For a simple example of a .tdda JSON file, see

    tdda/constraints/examples/example_constraints.tdda

For a fuller example, see:

    tdda/constraints/examples/elements92.tdda

For a description of the `.tdda` file format, see:

    tdda/constraints/examples/tdda_json_file_format.md

Run tests with

    python testbase.py
    python testpdconstraints.py


