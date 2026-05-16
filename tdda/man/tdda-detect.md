# "TDDA DETECT" 1 "January 2026" "3.0" "tdda detect manual"

## NAME

`tdda detect` - Detect data that does not obey supplied constraints

## SYNOPSIS

`tdda detect` [-h] [-?] [-7] [--no-config] [--colour] [--no-colour]
            [-epsilon EPSILON] [-o REPORT_PATH] [-a] [-f]
            [-t {strict,sloppy}] [--write-all-records]
            [--per-constraint] [--no-per-constraint]
            [--no-original-fields] [--original-fields]
            [--no-output-fields] [--output-fields [OUTPUT_FIELDS ...]]
            [-r [REPORT ...]] [--interleave] [--no-interleave]
            [--index] [--int] [--key [KEY ...]]
            [--verify-required-fields] [--verify-allowed-fields]
            [--no-verify-required-fields] [--no-verify-allowed-fields]
            [--varf] [--no-varf] [--pandas] [--polars]
            [--backend BACKEND]
            *INPUT* [*CONSTRAINTS* [*OUTPUT*]]

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

*OUTPUT* specifies the destination for detected records.

This is usually a file if the input was a file (e.g. a `.csv`
file or a `parquet` file), but does not have to be the same type.
If the input is a database table, the output is always a database
table in the same database.

## DESCRIPTION

The `tdda detect` command finds and reports data that fails to satisfy
the constraints in the *CONSTRAINTS* file specified. It also performs all
the same functions as `tdda verify`.

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

`-r`, `--report` [*REPORT* ...]  
                        Report formats to write, space-separated.  
                        Formats: `html`, `md` (`markdown`), `txt` (`text`),  
                        `json`, `yaml`, `toml`.  
                        The stem of the output file is taken from  
                        *REPORT_PATH* if `-o` is given, otherwise from  
                        *OUTPUT*.  
`-t`, `--type_checking` {*strict*,*sloppy*}  
                        "sloppy" means consider all numeric types  
                        equivalent  
`-o`, `--report-path` *REPORT_PATH*  
                        Stem path for report files (extension is replaced  
                        by the format).  

`--write-all-records`   Include passing records  
`--per-constraint`      Write one flag column per failing constraint in  
                        addition to n_failures. Set by default.  
`--no-per-constraint`   Do not write out any per-constraint flag columns  
`--no-original-fields`  Do not write out original fields columns  
`--original-fields`     Write out original fields columns (default)  
`--no-output-fields`    Do not write out any original fields in the output. By  
                        default, all original columns will be included.  
`--output-fields` [*OUTPUT_FIELDS* ...]  
                        Specify original columns to write out.  
`--interleave`          Interleave ok columns with original fields.  
`--no-interleave`       Do not interleave ok columns with original fields.  
`--index`               Include a row-number index in the output file when  
                        detecting. Rows are usually numbered from 1,  
                        unless the input file already has an index.  
`--int`                 Write out boolean fields as integers, with 1 for true  
                        and 0 for false.  
`--key [KEY ...]`       Key or key fields to use when reporting failures  

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

1) `tdda detect elements.parquet elements.tdda elements-failures.parquet`

This command reads data from `elements.parquet`, checks it against the
constraints in `elements.tdda`, and writes records with one or more
constraint failures to `elements-failures.parquet`.

2) `tdda detect elements.parquet elements.tdda elements-failures.parquet -r html -o elements`

As above, and also writes an HTML report to `elements.html`.

3) `tdda detect elements.parquet elements.tdda elements-failures.parquet -r md json txt -o elements`

As above, and also writes reports to `elements.md`, `elements.json`,
and `elements.txt`.

## SEE ALSO

tdda-verify(1),
tdda-discover(1),
tdda-serial(1)
