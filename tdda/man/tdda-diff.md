# "TDDA DIFF" 1 "%%DATE%%" "%%VERSION%%" "tdda diff manual"

## NAME

`tdda diff` — compare csv or parquet files

## SYNOPSIS

`tdda diff` [`--fields` *FIELD1,FIELD2*,...]
            [`--xfields` *FIELD1,FIELD2*,...  ]
            [`--horizontal`] [`-H`] [`--vertical`] [`-V`]
            [`--find-md`] [`--no-md`]
            [`--maxdiffs` *N*] [`--key` *FIELD*]
            [`--mono`] [`--bw`] [`--colours` *COLOURS*] [`-c` *COLOURS*]
            [`--dps` *N*]  [`--precision` *N*]
            [`--AE`] [`--LR`] [`--angles`] [`--pm`]
            [`--prefixes` *PREFIXES*]
            [`-N`] [`--no-config`]
            [`--strict`] [`--medium`] [`--loose`] [`--permissive`]
            *LEFT* *RIGHT*

## POSITIONAL ARGUMENTS

*LEFT* The first dataset to be compared, as a parquet or flat file
       (e.g. CSV), optionally using `:` format to specify flat-file metadata
       (see the help for `tdda serial`).
       (Normally thought of as left or actual)

*RIGHT* The second dataset to be compared as a parquet or flat file
        (e.g. CSV), optionally using `:` format to specify flat-file metadata
        (see the help for `tdda serial`).
        (Normally thought of as right, expected, reference, etc.)


## DESCRIPTION

The `tdda diff` command compares two tabular datasets in CSV or Parquet
files and shows some or all differences. It uses the same underlying
functionality as the `tdda.referencetest` assertions such as
`assertDataFramesEqual`, and provides similar control over what
differences to consider, e.g. which fields, and strictness of type and
numeric comparisons. It also provides a number of options for controlling
the display of differences.

By default, comparisons are row-based and consider all fields (columns),
as typed values after reading.

## OPTIONS

`*` indicates options that are the default behaviours

`--fields` *FIELD1,FIELD2*,...  
  Check only these fields (comma-separated list)

`--xfields` *FIELD1,FIELD2*,...  
  Check all fields except these (comma-separated list)

`--horizontal`, `-H`  
  Horizontal display (left and right, side by side)

`--vertical`, `-V`  
  Vertical display (left above right)


`--find-md`  
  Attempt to find associated metadata for flat files.

`--no-md`, `--no-find-md`  
  Do not attempt to find associated metadata for flat files.

`--key` *FIELD*  
  Use this field as a join key when reporting differences.

`--maxdiffs` *N*  
  Maximum number of differences to show.


`--mono`  
  Show monochrome output with different values in bold
  and shared values dimmed.

`--bw`  
  Show black and white output with different values in bold and shared
  values in the terminal's default style.

`--colours` *COLOURS*, `-c` *COLOURS*  
  Use colours specified e.g. `-c red-blue`


`--dps` *N*  
  Number of decimal places to show for floating-point values.
  Also sets precision if not specified separately.

`--precision` *N*  
  Precision for floating point comparisons. Two floats `a` and `b` will be
  considered equal if `abs(a - b) < 1e-`*N*.

`--AE`  
  Use `A:` and `E:` as labels for the two datasets (actual/expected)

`--LR`  
  Use `L:` and `R:` as labels for the two datasets (left/right)

`--angles`  
  Use `<` and `>` as labels for the two datasets

`--pm`  
  Use `+` and `-` as labels for the two datasets


`--prefixes` *PREFIXES*  
  Use prefixes specified as labels for the two datasets
  e.g. `--prefixes "actual:-ref:"` or `"actual: -ref: "` to include spaces


`-N`, `--no-config`  
  Use default configuration (ignore `~/.tdda.toml`)

`--strict`  
  Use strict type comparisons

`--medium`  
  Use medium-strictness type comparisons

`--loose`  
  Use loose (permissive) type comparisons

`--permissive`  
  Use loose (permissive) type comparisons

`--pandas`, `--pd`          Use Pandas as DataFrame engine. *  
`--polars`, `--pl`          Use Polars as DataFrame engine.  
`--backend`, `-B` *BACKEND*   Backend choice for Pandas  
                        (when dataframe engine is Pandas)  
                            `n` for numpy_nullable *  
                            `a` for pyarrow  
                            `o` for original.  



`--help`, `-?`, `--?`  
  Show help on `tdda diff`.


## EXAMPLES

Data suitable for all examples can be obtained with

`tdda examples diff`

1) `tdda diff a.csv a.csv`  

This is the simplest form of the command. It will read `a.csv` and
convert it to a data frame, using the default back end (Pandas).

2) `tdda diff a.csv b.csv --vertical`  

Compare two CSV files, stacking left and right values vertically
rather than side by side. Useful when there are many columns or
long values.

3) `tdda diff before.parquet after.parquet --key Income,Expenditure`  

Compare two Parquet files using a composite join key. The fields
`Income` and `Expenditure` must form a primary key in both datasets.
Rows are matched by key rather than by position.

4) `tdda diff actual.csv expected.csv --AE --bw`  

Compare two CSV files using `A:` and `E:` as markers for actual and
expected, with monochrome bold highlighting instead of colour.

5) `tdda diff foo.csv: bar.csv:`  

Compare two CSV files, asking TDDA to find associated metadata files
for each using naming conventions (e.g. `@.serial` or
`foo-metadata.json` in the same directory).

6) `tdda diff foo.csv bar.txt:money.serial`  

Compare `foo.csv` (loaded with default settings) against `bar.txt`,
using `money.serial` as the metadata file describing its format.

7) `tdda diff a.parquet b.csv --loose --dps 3`  

Compare a Parquet file against a CSV file with loose type matching
and floating-point values compared to 3 decimal places.

