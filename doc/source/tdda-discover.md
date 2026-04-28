# Command: `tdda discover`


## NAME

`tdda discover` - automatically generate constraints for data

## SYNOPSIS
```
tdda discover [-h] [-?] [-7] [--no-config] [--colour]
              [--no-colour] [-x] [-X] [-g] [-G]
              [-r REPORT ...] [-o REPORT_PATH]
              [--no-md] [--allowed] [--no-allowed]
              [--required] [--no-required] [--no-ar]
              [--pandas] [--polars] [--backend BACKEND]
              INPUT [CONSTRAINTS]
```
## POSITIONAL ARGUMENTS

*INPUT* is one of:
  - a CSV file or other flat file (e.g. `.csv`, `.txt`, `.psv`)
  - a data frame in a Parquet files (.parquet)
    e.g. from pandas, polars, R
  - Tables from PostgreSQL databases (e.g. `postgres:tablename`)
  - Tables from MySQL databases (e.g. `mysql:tablename`)
  - Tables from SQLite databases (e.g. `sqlite:tablename`)
  - Standard input (stdin): Use `-` to read from stdin
    Metadata for flat files can also be specified or inferred.

(Use `tdda help serial`, `tdda serial --help`, or `man tdda-serial`
for more information.)

*CONSTRAINTS* Name of the (JSON) constraints file to create.
  - Will use `.tdda` extension if no extention is specified.
  - Can be missing or `-` to write to standard output.

## DESCRIPTION

The `tdda discover` command is used to find constraints that are satisfied
(in most cases) by the input ("training") data provided.

## OPTIONS

The following options are available.

`*` indicates options that are the default beaviours

`-h`, `--help`            Show this help message and exit  
`-?`, `--?`               Same as `-h` or `--help`  
`-7`, `--ascii`           Report without using special characters  
`-N`, `--no-config`       Skip loading ~/.tdda.toml  
`--colour`                Use colour in terminal output *  
`--no-colour`             Do not not use colour in terminal output  
`-x`, `--rex`             Include regular expression generation  
`-X`, `--no-rex`          Exclude regular expression generation *  
`-g`, `--group-rex`       Group regular expression generation  
`-G`, `--no-group-rex`    Do not group regular expression generation *  

`-r`, `--report` [*REPORT* ...]       Report formats to write.  
`-o`, `--report-path` *REPORT_PATH*   Path for reports  

`--no-md`                 Do not create metadata in constraints file
`--allowed`               Create allowed-fields constraint (default)  
`--no-allowed`            Do not create allowed-fields constraint  
`--required`              Create required-fields constraint (default)  
`--no-required`           Do not create required-fields constraint
`--no-allowed-required`   Same as `--no-allowed --no-required`  
`--no-ar`                 Same as `--no-allowed --no-required`  
`--pandas`, `--pd`          Use Pandas as DataFrame engine. *  
`--polars`, `--pl`          Use Polars as DataFrame engine.  
`--backend`, `-B` *BACKEND*   Backend choice for Pandas  
                        (when dataframe engine is Pandas)  
                            `n` for numpy_nullable *  
                            `a` for pyarrow  
                            `o` for original.  

## EXAMPLES

(The example data be obtained by running 'tdda examples', which will create
various directories, including constraints_examples, containing the source
data for these examples.)

1) `tdda discover elements.parquet elements.tdda`

This command will read data from elements.parquet and (attempt to
find) constraints satifisfied by every record, and the data
collectively.  By default this will may include minimum and maximum
constraints on field values or lengths, nullability constraints,
uniqueness constraints, sign constraints, and allow-values
constraints.

The results will be written to elements.tdda in a JSON format,
including metadata.  The output constraints file, elements.tdda can be
used with 'tdda verify', to which constriants another datasets with
the same structure, are satisified, or with 'tdda detect', to find
which records and/or values fail to satisfy the constraints. The TDDA
can be edited (carefully) by hand, or programmatically, to add,
remove, tighten, or loosen constraints.

2) `tdda discover elements.csv`

This command is almost the same as the first except that it reads data
from the CSV file specified, and writes the constraints to the screen
(standard output).

The CSV structure and field types will normally be inferred (possibly
incorrectly) by TDDA, and if the inference is bad, the command may
fail. If there is a file in the same directory with a name suggesting
it is associated metadata describing the csv file, that will be
used. Typical such files include:

`elements.serial`         - a `tdda.serial` metadata specification  
`elements.csv.serial`     - a `tdda.serial` metadata specification  
`elements_metadata.json`  - a CSVW (CSV on the Web) specification  
`elements.table.json`     - a Frictionless table specification (JSON)  
`elements.table.yaml`     - a Frictionless table specification (YAML)  

3) `tdda discover --rex md.serial:elements.parquet`

This is similar to the last two except that:
  - regular expression inference is requested (`--rex`) for text fields.
    Rexpy will be used to attempt to infer one or a few regular
    expressions that characterize each field in the input data.
  - a metadata filed to be used to interpret the `.csv` file is provided
    explicitly.

4) `tdda discover --rex postgres:elements`

This is similar again except that now the postgres:specifier will be
interpreted as a database connection file in the user's home
directory, with the name `~/.dbCredential.postgres`. This file should
contain connection information for a supported database. The extension
`.postgres` does not itself mean that this is a PostgreSQL database,
though that is a common convention. Use one of

`tdda help db`  
`tdda help database`  

to get help with the database connection file format.

## SEE ALSO

tdda-verify(1),
tdda-detect(1),
tdda-serial(1)
