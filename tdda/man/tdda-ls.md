# "TDDA LS" 1 "%%DATE%%" "%%VERSION%%" "tdda ls manual"

## NAME

`tdda ls` — List fields in a dataset

## SYNOPSIS

`tdda ls` [`-h`] [`-1`|`--one-line`] [`-l`] [`--pandas`] [`--polars`]
         [`--backend` *BACKEND*]
         *INPUT*

## POSITIONAL ARGUMENTS

*INPUT* is one of:
  - a CSV file (or `.tsv`, `.psv`, `.txt`)
  - a Parquet file (`.parquet`)
  - a flat file with colon syntax to trigger metadata lookup
    (e.g. `foo.csv:`)
  - a flat file with an explicit metadata path
    (e.g. `foo.csv:foo.serial`)

## DESCRIPTION

The `tdda ls` command lists the fields in a dataset.

Without `--long`, it prints a one-line summary followed by the field
names, right-aligned.

With `--long`, it prints a one-line summary followed by a table showing
each field's dtype, minimum value, maximum value, and null count.

For flat files, a second line reports how the file was read and which
metadata file was used, if any.

## OPTIONS

`-h`, `-?`, `--help`        Show this help message and exit  

`-1`, `--one-line`          List all field names on one line, space-separated  
`-l`, `--long`              Show dtype, min, max, and null count per field  

`--pandas`, `--pd`          Use Pandas as DataFrame engine (default)  
`--polars`, `--pl`          Use Polars as DataFrame engine  
`--backend`, `-B` *BACKEND*   Backend choice for Pandas  
                          `n` for numpy_nullable *  
                          `a` for pyarrow  
                          `o` for original  

## EXAMPLES

The example data can be obtained by running `tdda examples`, which will
create various directories, including `serial_examples`.

1) `tdda ls accounts1k.parquet`

List the fields in `accounts1k.parquet`.

2) `tdda ls -l accounts1k.csv:`

Show field details for `accounts1k.csv`, using any associated metadata
file found automatically.

3) `tdda ls -l accounts1k.csv --polars`

Show field details using Polars.

## SEE ALSO

`tdda-diff(1)`,
`tdda-serial(1)`,
`tdda-verify(1)`
