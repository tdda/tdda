# "TDDA SAMPLE" 1 "%%DATE%%" "%%VERSION%%" "tdda sample manual"

## NAME

`tdda sample` — Display N random rows from a dataset

## SYNOPSIS

`tdda sample` [`-h`] [`N`] [`--seed` *SEED*]
              [`--fields` *FIELDS*] [`--xfields` *FIELDS*]
              [`--pandas`] [`--polars`] [`--backend` *BACKEND*]
              *INPUT* [*FIELD* ...]

## POSITIONAL ARGUMENTS

*INPUT*      Dataset path (CSV, Parquet, or colon syntax).

*FIELD* ...  Field names (or `fnmatch` wildcard patterns) to display.
           Fields appear in the order given. Equivalent to `--fields`;
           both may be combined. Wildcards must be quoted in the shell.

## DESCRIPTION

The `tdda sample` command displays N randomly selected rows from a dataset
(default 10) as a rich table.

When no `--seed` is given, a random seed is chosen automatically and printed
so the result can be reproduced.

Null values are shown as `∅`.

## OPTIONS

`-h`, `-?`, `--help`        Show this help message and exit  

`N`                       Number of random rows to show (default 10)  

`--seed` *SEED*             Random seed. If omitted, a seed is chosen
                          automatically and printed.  

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

1) `tdda sample accounts1k.parquet`

Display 10 random rows from `accounts1k.parquet`, printing the seed used.

2) `tdda sample 50 accounts1k.csv:`

Display 50 random rows, using any associated metadata file.

3) `tdda sample 20 --seed 42 accounts1k.csv:`

Display 20 random rows with a fixed seed (reproducible).

4) `tdda sample --fields 'name,balance' accounts1k.csv:`

Display 10 random rows showing only `name` and `balance`.

## SEE ALSO

`tdda-cat(1)`,
`tdda-head(1)`,
`tdda-tail(1)`,
`tdda-ls(1)`,
`tdda-diff(1)`,
`tdda-serial(1)`
