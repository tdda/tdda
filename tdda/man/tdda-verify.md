# "TDDA VERIFY" 1 "January 2026" "3.0" "tdda verify manual"

## NAME

`tdda verify` - Veriify that constraints are satisfied by data

## SYNOPSIS

`tdda verify` [`-h`] [`-?`] [`-7`] [`--no-config`]
            [`--colour`] [`--no-colour`]
            [`-epsilon EPSILON`] [`-a`] [`-f`] [`-r` [*REPORT* ...]]
            [`-t {strict,sloppy}`] [`--verify-required-fields`]
            [`--verify-allowed-fields`] [`--no-verify-required-fields`]
            [`--no-verify-allowed-fields`] [`--varf`] [`--no-varf`]
            [`--pandas`] [`--polars`] [`--backend` *BACKEND*]
            *INPUT* [*CONSTRAINTS*]

## POSITIONAL ARGUMENTS

*INPUT* is one of:
  - a csv file or other flat file (e.g. .csv, .txt, .psv)
  - a data frames in a Parquet files (.parquet)
    e.g. from pandas, polars, R
  - Tables from PostgreSQL databases (e.g. postgres:tablename)
  - Tables from MySQL databases (e.g. mysql:tablename)
  - Tables from SQLite databases (e.g. sqlite:tablename)
  - Standard input, stdin. Use `-` to read specify this.

Metadata for flat files can also be specified or inferred.
Use `tdda help serial`, `tdda serial --help`, or `man tdda-serial` for
more information.

*CONSTRAINTS*, if provided, is a JSON .tdda file containing
constraints.

If no constraints file is provided, a file with the same path as
the input file, with a .tdda extension will be tried.

## DESCRIPTION

The `tdda verify` command is used to check that data conforms
the the constraints specified. Any constraints not satisfied
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
`--no-colour`             Do not not use colour in terminal output  

`--epsilon` *EPSILON*       Epsilon fuzziness (tolerance for comparisons)  

`-a`, `--all`               Report all fields, even if there are no  
                        failures  
`-f`, `--fields`            Report only fields with failures  

`-r`, `--report` [*REPORT* ...]  
                        Report formats to write.  
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
                        (When dataframe engine is Pandas)  
                          `n` for numpy_nullable *  
                          `a` for pyarrow  
                          `o` for original.  

## SEE ALSO

tdda-detect(1),
tdda-discover(1),
tdda-serial(1)
