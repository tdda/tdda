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
            LEFT RIGHT
```
#### POSITIONAL ARGUMENTS

*LEFT* The 'left' (or actual) on-disk data frame for comparison, usually
supplied as a parquet file or a flat file, with or without metadata.

*RIGHT* The 'right' (or expected) on-disk data frame for comparison, usually
supplied as a parquet file or a flat file, with or without metadata.


#### DESCRIPTION

The `tdda diff` command compares two tabular datasets in CSV or Parquet
files and shows some or all differences. It uses the same underlying
functionality as the `tdda.referencetest` assertions such as
`assertDataFramesEqual`, and provides similar control over what
differences to consider, e.g. which fields, and strictness of type and
numeric comparisons. It also provides a number of options for controlling
the display of differences.

The `tdda diff` functionality always first builds dataframes from the
*LEFT* and *RIGHT* sources. The datasets are then compared and differences
reported.

If no key is provided, rows are compared based on position in the file,
i.e. row *n* in the left file is compared to row *n* in the right file.
If the files contain different numbers of rows, the shorter on is
considered to have "blanks" at the end, (these being shown differently
from nulls. The `--engine` and `--backend` options give control over
the data frame engine and backend (in the case of Pandas).

If key is provided (which should uniquely identify rows), the right
data frame is joined to the left data frame using an outer join,
and the joined rows are compared.

By default, all fields are considered and comparisons are typed.
Options, including `--strict`, `--medium`, `--loose` and `--precision`
control various aspects of the comparison, and the `--fields` and
`--xfields` options can be used to restrict the fields compared
and reported.

If no (qualifying) differences are found, the output is empty.

If differences are found, summary information is reported
followed by a difference table. The layout, colouring, and other
aspects of styling of the output tables can be controlled with
options.


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

`--colours`, `-c` *COLOURS*  
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


#### EXAMPLES

Data suitable for all examples can be obtained with

`tdda examples diff`

1. tdda diff a.csv a.csv

This is the simplest form of the command. It will read a.csv and
convert it to a data frame, using the default back end (Pandas).

