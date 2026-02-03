# "TDDA DIFF" 1 "January 2026" "3.0" "tdda diff manual"

## NAME

`tdda diff`  -- compare csv or parquet files

## SYNOPSIS

`tdda diff` [`--fields` *FIELD1,FIELD2*,...]
            [`--xfields` *FIELD1,FIELD2*,...  ]
            [`--horizontal`] [`-H`] [`--vertical`] [`-V`]
            [`--maxdiffs` *N*]
            [`--mono`] [`--bw`] [`--colours`, `-c`, `--colours` *COLOURS*]
            [`--dps` *N*]  [`--precision` *N*]
            [`--AE`] [`--LR`] [`--angles`] [`--pm`]
            [`--prefixes` *PREFIXES*]
            [`--no-config`]
            [`--strict`] [`--medium`] [`--loose`] [`--permissive`]
            *LEFT* *RIGHT* [*OUTPATH*]

## POSITIONAL ARGUMENTS

*LEFT*

*RIGHT*

*OUTPATH*

## DESCRIPTION

The `tdda diff` command compares two tabular datasets in CSV or Parquet
files and shows some or all differences. It uses the same underlying
functionality as the `tdda.referencetest` assertions such as
`assertDataFramesEqual`, and provides similar control over what
differences to consider, e.g. which fields, and strictness of type and
numeric comparisons. It also provides a number of options for controlling
the display of differences.

By default, comparisons are row-based and consider all fields (columns),
as typed values after reading. Ke

## OPTIONS

`--fields` *FIELD1,FIELD2*,...  
  Check only these fields (comma-separated list)

`--xfields` *FIELD1,FIELD2*,...  
  Check all fields except these (comma-separated list)

`--horizontal`, `-H`,  
  Horizontal dispay (left and right, side by side)

`--vertical`, `-V`,  
  Vertical dispay (left above right)


`--maxdiffs` *N*  
  Maximum number of differences to show.


`--mono`  
  Show monochrome output. Also enables --LR by default

`--bw`  
  Show black and white output. Also enables --LR by default

`--colours`, `-c`, `--colours` *COLOURS*  
  Use colours specified e.g. -c red-blue


`--dps` *N*  
  Number of decimal places to show for floating-point values.
  Also sets precision if not specified separately

`--precision` *N*  
  Precision for floating point comparisons. Two floats `a` and `b` will be
  considered equal if `abs(a - b) < 1e-`*N*.

`--AE`  
  Use `A:` and `E:` as labels for the two datasets (actual/expected)

`--LR`  
  Use `L:` and `R:`  as labels for the two datasets (left/right)

`--angles`  
  Use `<` and `>` as labels for the two datasets

`--pm`  
  Use `+` and `-` as labels for the two datasets


`--prefixes` *PREFIXES*  
  Use prefixes specified as labels for the two datasets
  e.g. --prefixes "actual: -ref: "


`--no-config`  
  Use default configuration (ignore ~/.tdda.toml)

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

1. tdda diff a.csv a.csv

This is the simplest form of the command. It will read a.csv and
convert it to a data frame, using the default back end (Pandas).

