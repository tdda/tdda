### Command: `tdda diff`


#### NAME

`tdda diff`  -- compare csv or parquet files

#### SYNOPSIS
```x
tdda diff [--fields FIELD1,FIELD2,...]
            [--xfields FIELD1,FIELD2,...  ]
            [--horizontal] [-H] [--vertical] [-V]
            [--maxdiffs N]
            [--mono] [--bw] [--colours, -c, --colours COLOURS]
            [--dps N]  [--precision N]
            [--AE] [--LR] [--angles] [--pm]
            [--prefixes PREFIXES]
            [--no-config]
            [--strict] [--medium] [--loose] [--permissive]
            LEFT RIGHT [OUTPATH]
```
#### POSITIONAL ARGUMENTS

*LEFT*

*RIGHT*

*OUTPATH*

#### DESCRIPTION

The `tdda diff` command compares two tabular datasets in CSV or Parquet
files and shows some or all differences. It uses the same underlying
functionality as the `tdda.referencetest` assertions such as
`assertDataFramesEqual`, and provides similar control over what
differences to consider, e.g. which fields, and strictness of type and
numeric comparisons. It also provides a number of options for controlling
the display of differences.

By default, comparisons are row-based and consider all fields (columns),
as typed values after reading. Ke

#### OPTIONS

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


`--help`, `-?`, `--?`  
  Show help on `tdda diff`.


#### EXAMPLES

1. tdda diff --mono a.csv b.csv


Difference summary:  
DataFrames have same structure, but different values.  
Total number of different values: 2 of 24 (8.33%).  
Total number of rows with differences: 2  
Total number of columns with differences: 2:  
           1: sq  
           1: name  
  
**Value Differences (all rows with differences)**  
┏━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┓  
┃      ┃    **sq** ┃    **sq** ┃   **name** ┃   **name** ┃  
┃      ┃ **Int64** ┃ **Int64** ┃ **string** ┃ **string** ┃  
┃  **row** ┃     < ┃     > ┃      < ┃      > ┃  
┡━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━┩  
│    2 │     9 │     9 │  **three** │  **Three** │  
│    3 │    **16** │    **15** │   four │   four │  
└──────┴───────┴───────┴────────┴────────┘  
