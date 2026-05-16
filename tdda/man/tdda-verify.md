# "TDDA VERIFY" 1 "January 2026" "3.0" "tdda verify manual"

## NAME

`tdda verify` - Verify that constraints are satisfied by data

## SYNOPSIS

`tdda verify` [`-h`] [`-?`] [`-7`] [`--no-config`]
            [`--colour`] [`--no-colour`]
            [`--epsilon` *EPSILON*] [`-a`] [`-f`]
            [`-t {strict,sloppy}`] [`--verify-required-fields`]
            [`--verify-allowed-fields`] [`--no-verify-required-fields`]
            [`--no-verify-allowed-fields`] [`--varf`] [`--no-varf`]
            [`--pandas`] [`--polars`] [`--backend` *BACKEND*]
            *INPUT* [*CONSTRAINTS*]

## POSITIONAL ARGUMENTS

*INPUT* is one of:
  - a CSV file or other flat file (e.g. `.csv`, `.txt`, `.psv`),
    optionally using `:` format to specify flat-file metadata
    (see the help for `tdda serial`)
  - a data frame in a Parquet file (`.parquet`)
    e.g. from pandas, polars, R
  - a table from PostgreSQL databases (e.g. `postgres:tablename`)
  - a table from MySQL databases (e.g. `mysql:tablename`)
  - a table from SQLite databases (e.g. `sqlite:tablename`)
  - Standard input (stdin): Use `-` to read from stdin

*CONSTRAINTS*, if provided, is a JSON `.tdda` file containing
constraints.

If no constraints file is provided, a file with the same path as
the input file, with a `.tdda` extension will be tried.

## DESCRIPTION

The `tdda verify` command is used to check that data conforms
to the constraints specified. Any constraints not satisfied
by the data are reported, together with summary statistics.

The `tdda verify` command does *not* report which records and
values cause constraints to be violated: the companion command
`tdda detect` performs this function.

## OPTIONS

`-h`, `--help`              Show this help message and exit  
`-?`, `--?`                 Same as `-h` or `--help`  
`-7`, `--ascii`             Report without using special characters  
`-N`, `--no-config`         Skip loading `~/.tdda.toml`  

`--colour`                Use colour in terminal output  
`--no-colour`             Do not use colour in terminal output  

`--epsilon` *EPSILON*       Epsilon fuzziness (tolerance for comparisons)  

`-a`, `--all`               Report all fields, even if there are no  
                        failures  
`-f`, `--fields`            Report only fields with failures  

`-t`, `--type_checking` {*strict*,*sloppy*}  
                        "sloppy" means consider all numeric types  
                        equivalent  

`--verify-required-fields`, `--vrf`
                        Force verify of required fields  
`--verify-allowed-fields`, `--vaf`  
                        Force verify of allowed fields  
`--no-verify-required-fields`, `--no-vrf`  
                        Force no verication of required fields  
`--no-verify-allowed-fields`, `--no-vaf`  
                        Force no verification of allowed fields  
`--varf`, `--vraf`          Force verification of allowed and required  
                        fields  
`--no-varf`, `--no-vraf`    Force no verification of allowed and required  
                        fields  

`--pandas`, `--pd`          Use Pandas as DataFrame engine.  
`--polars`, `--pl`          Use Polars as DataFrame engine.  
`--backend`, `-B` *BACKEND*   Backend choice for Pandas  
                        (when dataframe engine is Pandas)  
                          `n` for numpy_nullable *  
                          `a` for pyarrow  
                          `o` for original.  

## EXAMPLES

The example data can be obtained by running `tdda examples`, which will
create various directories, including `constraints_examples`, containing
source data for these examples.

1) `tdda verify elements.parquet elements.tdda`

This command reads data from `elements.parquet` and checks it against the
constraints in `elements.tdda`, reporting any constraints that are not
satisfied.

## SEE ALSO

tdda-detect(1),
tdda-discover(1),
tdda-serial(1)
