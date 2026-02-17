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
            *LEFT* *RIGHT*

## POSITIONAL ARGUMENTS

*LEFT* The 'left' (or actual) on-disk data frame for comparison, usually
supplied as a parquet file or a flat file, with or without metadata.
See the section METADATA below for information about metadata matching rules.

*RIGHT* The 'right' (or expected) on-disk data frame for comparison, usually
supplied as a parquet file or a flat file, with or without metadata.


## DESCRIPTION

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
from nulls. The `--polars` and `--backend` options give control over
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


## EXAMPLES

Data suitable for all examples can be obtained with `tdda examples diff`,
from a directory in which you are happy for files to be written.

`tdda examples diff`

1. tdda diff a.parquet b.parquet

Compare dataframes read from a.parquet and b.parquet
(with all default settings).

There is no output if they are the same

2. tdda diff a.csv b.csv

As above, but now creating dataframes from CSV files using default
settings (unless matching metadata is found, in which case it will
be used).

3. tdda diff a.tsv b.psv

As above, except the `.tsv' and `.psv` extensions will cause the
separator fo the flat files to be set as TAB and PIPE (|)
respectively.

4. tdda diff a.csv b.txt:md.serial

As above except that metadata for b.txt will be sought in md.serial,
which will be assumed to be a `tdda.serial` flat-file metadata
specification file. Alternative formats for metadata are
CSVW (typically md-metadata.json) or Frictionless (typically md.table.json
or md.table.yaml).

5. tdda diff a.csv b.csv --fields 'row,sq,recip'

As above, but restrict attention to fields `row`, `sq`, and `recip`.
(These need not exist.)

5. tdda diff a.csv b.csv --xfields 'name,even,date'

As above, but ignore any fields called `name`, `even`, or `date`.
(These need not exist.)

6. tdda diff a.csv b.csv --vertical

As above, but shows rows from the left and right datasets on separate lines,
rather than on a single line interleaved (the default, --horizontal).
Useful for wide datasets.

7. tdda diff a.csv b.csv --precision 2

As above, but sets the precision for floating-point comparisons to 2
decimal places, i.e. do report differences if the floating-point values
both round to the same value to 2 decimal places.

8. tdda diff a.parquet b.tsv --maxdiffs 1

As above, but stop reporting limit the table to 1 row of differences.
(The summary still includes all rows.)

9. tdda diff a.psv b.parquet --polars

As above, but use polars dataframes.

10. tdda diff a.psv b.parquet --backend n

As above, but use pandas with the `numpy_nullable` backend.

11. tdda diff a.csv z.csv --key row
