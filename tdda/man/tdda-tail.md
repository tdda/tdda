# "TDDA TAIL" 1 "%%DATE%%" "%%VERSION%%" "tdda tail manual"

## NAME

`tdda tail` — Display the last N rows of a dataset

## SYNOPSIS

`tdda tail` [`-h`] [`N`]
            [`--fields` *FIELDS*] [`--xfields` *FIELDS*]
            [`--pandas`] [`--polars`] [`--backend` *BACKEND*]
            *INPUT* [*FIELD* ...]

## POSITIONAL ARGUMENTS

*INPUT*      Dataset path (CSV, Parquet, or colon syntax).

*FIELD* ...  Field names (or `fnmatch` wildcard patterns) to display.
           Fields appear in the order given. Equivalent to `--fields`;
           both may be combined. Wildcards must be quoted in the shell.

## DESCRIPTION

The `tdda tail` command displays the last N rows of a dataset (default 10)
as a rich table.

Null values are shown as `∅`.

## OPTIONS

`-h`, `-?`, `--help`        Show this help message and exit  

`N`                       Number of rows to show (default 10)  

`--fields` *FIELDS*         Show only these fields. *FIELDS* is a
                          comma- or space-separated list of field names
                          or `fnmatch` wildcard patterns (e.g. `eu_*`,
                          `[a-z]*`). Fields appear in the order
                          specified. Requires quoting in the shell when
                          using spaces or wildcards.  

`--xfields` *FIELDS*        Exclude these fields. Same format as
                          `--fields`. Fields appear in dataset order.  

`--pandas`, `--pd`          Use Pandas as DataFrame engine (default)  
`--polars`, `--pl`          Use Polars as DataFrame engine  
`--backend`, `-B` *BACKEND*   Backend choice for Pandas  
                          `n` for numpy_nullable *  
                          `a` for pyarrow  
                          `o` for original  

## EXAMPLES

1) `tdda tail accounts1k.parquet`

Display the last 10 rows of `accounts1k.parquet`.

2) `tdda tail 20 accounts1k.csv:`

Display the last 20 rows, using any associated metadata file.

3) `tdda tail --fields 'name,balance' accounts1k.csv:`

Display only `name` and `balance` for the last 10 rows.

## SEE ALSO

`tdda-cat(1)`,
`tdda-head(1)`,
`tdda-sample(1)`,
`tdda-ls(1)`,
`tdda-diff(1)`,
`tdda-serial(1)`
