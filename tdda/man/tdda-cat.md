# "TDDA CAT" 1 "%%DATE%%" "%%VERSION%%" "tdda cat manual"

## NAME

`tdda cat` — Display rows from a dataset as a rich table

## SYNOPSIS

`tdda cat` [`-h`] [`N` | `-N` | `+N`] [`-s` | `-S`]
           [`--fields` *FIELDS*] [`--xfields` *FIELDS*]
           [`-r` *N* [`--seed` *SEED*]]
           [`--pandas`] [`--polars`] [`--backend` *BACKEND*]
           *INPUT* [*FIELD* ...]

## POSITIONAL ARGUMENTS

*INPUT* is one of:
  - a CSV file (or `.tsv`, `.psv`, `.txt`)
  - a Parquet file (`.parquet`)
  - a flat file with colon syntax to trigger metadata lookup
    (e.g. `foo.csv:`)
  - a flat file with an explicit metadata path
    (e.g. `foo.csv:foo.serial`)

*FIELD* ...  Field names (or `fnmatch` wildcard patterns) to display.
           Fields appear in the order given. Equivalent to `--fields`;
           both may be combined. Wildcards must be quoted in the shell.

## DESCRIPTION

The `tdda cat` command displays rows from a dataset as a rich table.

Without a row count, all rows are shown.

  `N` or `-N`    First N rows  
  `+N`           Last N rows  

Null values are shown as `∅`.

## OPTIONS

`-h`, `-?`, `--help`        Show this help message and exit  

`--fields` *FIELDS*         Show only these fields. *FIELDS* is a
                          comma- or space-separated list of field names
                          or `fnmatch` wildcard patterns (e.g. `eu_*`,
                          `[a-z]*`). Fields appear in the order
                          specified. Requires quoting in the shell when
                          using spaces or wildcards.  

`--xfields` *FIELDS*        Exclude these fields. Same format as
                          `--fields`. Fields appear in dataset order.  

`-s`                        Short headers: column width driven by data;
                          headers split at word boundaries (punctuation
                          and lowercase→uppercase transitions) and packed
                          onto as few lines as possible.  

`-S`                        Short headers: as `-s` but split anywhere
                          (mid-word) to fit the data width.  

`-r` *N*, `--random` *N*      Show *N* random rows instead of a slice.  

`--seed` *SEED*             Random seed for `-r`. If omitted, a seed is
                          chosen automatically and printed.  

`--pandas`, `--pd`          Use Pandas as DataFrame engine (default)  
`--polars`, `--pl`          Use Polars as DataFrame engine  
`--backend`, `-B` *BACKEND*   Backend choice for Pandas  
                          `n` for numpy_nullable *  
                          `a` for pyarrow  
                          `o` for original  

## EXAMPLES

1) `tdda cat accounts1k.parquet`

Display all rows from `accounts1k.parquet`.

2) `tdda cat -10 accounts1k.csv:`

Display the first 10 rows, using any associated metadata file.

3) `tdda cat +10 accounts1k.csv:`

Display the last 10 rows.

4) `tdda cat --fields 'name,balance' accounts1k.csv:`

Display only the `name` and `balance` fields.

5) `tdda cat --fields 'amount*' --xfields '*_raw' accounts1k.csv:`

Display fields matching `amount*`, excluding those ending in `_raw`.

6) `tdda cat -r 20 --seed 42 accounts1k.csv:`

Display 20 random rows with a fixed seed.

7) `tdda cat -s accounts1k.csv:`

Display all rows with compact multi-line headers, splitting at word
boundaries (`open_date` → `open date`, `accountType` → `account Type`).

## SEE ALSO

`tdda-head(1)`,
`tdda-tail(1)`,
`tdda-sample(1)`,
`tdda-ls(1)`,
`tdda-diff(1)`,
`tdda-serial(1)`
