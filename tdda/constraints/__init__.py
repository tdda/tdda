"""
Constraint generation and verification for datasets, including
Pandas DataFrames.

For details of the full API for discovery and verification of
constraints:

    >>> import tdda.constraints.pdconstraints
    >>> help(tdda.constraints.pdconstraints)

To run the command-line tool for verifying constraints against a Pandas
dataframe using a feather dataframe file:

    python -m tdda.constraints.pdverify df.feather [constraints.tdda]

"""
