# Command Line Reference

## `tdda`


### NAME

`tdda` - test-driven data analysis

### SYNOPSIS
```
tdda discover      Generate constraints for data validation  
tdda verify        Verify (validate) data against constraints  
tdda detect        Detect data that fails constraints  

tdda examples      Copy the tdda example data and code  
tdda gentest       Auto-generate Python tests for code in any language  

tdda diff          Find difference in datasets in parquet or CSV files  
tdda serial        Convert or infer flat-file metadata in tdda.serial,  
                   CSVW, or Frictionless formats  
tdda tag           Tag tests that failed in the last reference test run  
tdda config        Show TDDA configuration  

tdda version       Print the TDDA version number  
tdda help          Print this help  
tdda help COMMAND  Print help on COMMAND (e.g. discover, verify)  

tdda test          Run the tdda library's self-tests.  
```
### OPTIONS

`-v`, `--version`       Print version number (same as tdda version)  
`-h`, `-?`, `--help`      Print this help  

### SEE ALSO

rexpy(1)

[TDDA Book](https://book.tdda.info)

---

## `tdda discover`


### NAME

`tdda discover` - automatically generate constraints for data

### SYNOPSIS
```
tdda discover [-h] [-?] [-7] [--no-config] [--colour]
              [--no-colour] [-x] [-X] [-g] [-G]
              [-r REPORT ...] [-o REPORT_PATH]
              [--no-md] [--allowed] [--no-allowed]
              [--required] [--no-required] [--no-ar]
              [--pandas] [--polars] [--backend BACKEND]
              INPUT [CONSTRAINTS]
```
### POSITIONAL ARGUMENTS

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

(Use `tdda help serial`, `tdda serial --help`, or `man tdda-serial`
for more information.)

*CONSTRAINTS* Name of the (JSON) constraints file to create.
  - Will use `.tdda` extension if no extension is specified.
  - Can be missing or `-` to write to standard output.

### DESCRIPTION

The `tdda discover` command is used to find constraints that are satisfied
(in most cases) by the input ("training") data provided.

### OPTIONS

The following options are available.

`*` indicates options that are the default behaviours

`-h`, `--help`            Show this help message and exit  
`-?`, `--?`               Same as `-h` or `--help`  
`-7`, `--ascii`           Report without using special characters  
`-N`, `--no-config`       Skip loading `~/.tdda.toml`  
`--colour`              Use colour in terminal output *  
`--no-colour`           Do not use colour in terminal output  
`-x`, `--rex`             Include regular expression generation  
`-X`, `--no-rex`          Exclude regular expression generation *  
`-g`, `--group-rex`       Group regular expression generation  
`-G`, `--no-group-rex`    Do not group regular expression generation *  

`-r`, `--report` [*REPORT* ...]       Report formats to write, space-separated.  
Formats: `html`, `md` (`markdown`), `txt` (`text`),
`json`, `yaml`, `toml`.
The stem of the output file is taken from
*REPORT_PATH* if `-o` is given, otherwise from
*CONSTRAINTS*.

`-o`, `--report-path` *REPORT_PATH*   Stem path for report files (extension  
is replaced by the format).

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

### EXAMPLES

The example data can be obtained by running 'tdda examples', which will create
various directories, including constraints_examples, containing the source
data for these examples.

1) `tdda discover elements.parquet elements.tdda`

This command will read data from elements.parquet and (attempt to)
find constraints satisfied by every record, and the data
collectively.  By default this can include minimum and maximum
constraints on field values or lengths, nullability constraints,
uniqueness constraints, sign constraints, and allow-values
constraints.

The results will be written to `elements.tdda` in a JSON format,
including metadata.  The output constraints file, `elements.tdda` can be
used with `tdda verify` to verify that another dataset with the same
structure satisfies the constraints, or with `tdda detect` to find
which records and/or values fail to satisfy the constraints. The `.tdda`
file can be edited (carefully) by hand, or programmatically, to add,
remove, tighten, or loosen constraints.

2) `tdda discover elements.csv`

This command is almost the same as the first except that it reads data
from the CSV file specified, and writes the constraints to the screen
(standard output).

The CSV structure and field types will normally be inferred (possibly
incorrectly) by TDDA, and if the inference is bad, the command may
fail. If you use:

`tdda discover elements.csv:format.serial`

metadata in `format.serial` will be used to guide the DataFrame
creation. If you use

`tdda discover elements.csv:`

it will look for any associated metadata for `elements.csv` using
naming conventions described in the help for `tdda serial`.


3) `tdda discover --rex md.serial:elements.parquet`

This is similar to the last two except that:
  - regular expression inference is requested (`--rex`) for text fields.
    Rexpy will be used to attempt to infer one or a few regular
    expressions that characterize each field in the input data.
  - a metadata file to be used to interpret the `.csv` file is provided
    explicitly.

4) `tdda discover elements.parquet elements.tdda -r html -o elements`

This discovers constraints as in example 1, and also writes an HTML
report to `elements.html`.

5) `tdda discover elements.parquet elements.tdda -r md json txt -o elements`

This discovers constraints as in example 1, and also writes reports
to `elements.md`, `elements.json`, and `elements.txt`.

6) `tdda discover --rex postgres:elements`

This is similar again except that now the postgres:specifier will be
interpreted as a database connection file in the user's home
directory, with the name `~/.dbCredential.postgres`. This file should
contain connection information for a supported database. The extension
`.postgres` does not itself mean that this is a PostgreSQL database,
though that is a common convention. Use one of

`tdda help db`  
`tdda help database`  

to get help with the database connection file format.

### SEE ALSO

tdda-verify(1),
tdda-detect(1),
tdda-serial(1)

---

## `tdda verify`


### NAME

`tdda verify` - Verify that constraints are satisfied by data

### SYNOPSIS
```
tdda verify [-h] [-?] [-7] [--no-config]
            [--colour] [--no-colour]
            [--epsilon EPSILON] [-a] [-f]
            [-t {strict,sloppy}] [--verify-required-fields]
            [--verify-allowed-fields] [--no-verify-required-fields]
            [--no-verify-allowed-fields] [--varf] [--no-varf]
            [--pandas] [--polars] [--backend BACKEND]
            INPUT [CONSTRAINTS]
```
### POSITIONAL ARGUMENTS

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

### DESCRIPTION

The `tdda verify` command is used to check that data conforms
to the constraints specified. Any constraints not satisfied
by the data are reported, together with summary statistics.

The `tdda verify` command does *not* report which records and
values cause constraints to be violated: the companion command
`tdda detect` performs this function.

### OPTIONS

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

### EXAMPLES

The example data can be obtained by running `tdda examples`, which will
create various directories, including `constraints_examples`, containing
source data for these examples.

1) `tdda verify elements.parquet elements.tdda`

This command reads data from `elements.parquet` and checks it against the
constraints in `elements.tdda`, reporting any constraints that are not
satisfied.

### SEE ALSO

tdda-detect(1),
tdda-discover(1),
tdda-serial(1)

---

## `tdda detect`


### NAME

`tdda detect` - Detect data that does not obey supplied constraints

### SYNOPSIS
```
tdda detect [-h] [-?] [-7] [--no-config] [--colour] [--no-colour]
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
            INPUT [CONSTRAINTS [OUTPUT]]
```
### POSITIONAL ARGUMENTS

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

### DESCRIPTION

The `tdda detect` command finds and reports data that fails to satisfy
the constraints in the *CONSTRAINTS* file specified. It also performs all
the same functions as `tdda verify`.

### OPTIONS

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

### EXAMPLES

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

### SEE ALSO

tdda-verify(1),
tdda-discover(1),
tdda-serial(1)

---

## `tdda diff`


### NAME

`tdda diff`  -- compare csv or parquet files

### SYNOPSIS
```
tdda diff [--fields FIELD1,FIELD2,...]
            [--xfields FIELD1,FIELD2,...  ]
            [--horizontal] [-H] [--vertical] [-V]
            [--find-md] [--no-md]
            [--maxdiffs N] [--key FIELD]
            [--mono] [--bw] [--colours, -c, --colours COLOURS]
            [--dps N]  [--precision N]
            [--AE] [--LR] [--angles] [--pm]
            [--prefixes PREFIXES]
            [-N] [--no-config]
            [--strict] [--medium] [--loose] [--permissive]
            LEFT RIGHT
```
### POSITIONAL ARGUMENTS

*LEFT* The first dataset to be compared, as a parquet or flat file (e.g. CSV),
       optionally using `:` format to specify flat-file metadata
       (see the help for `tdda serial`).
       (Normally thought of as left or actual)

*RIGHT*  The second dataset to be compared as a parquet or flat file (e.g. CSV),
         optionally using `:` format to specify flat-file metadata
         (see the help for `tdda serial`).
         (Normally thought of as right, expected, reference, etc.)


### DESCRIPTION

The `tdda diff` command compares two tabular datasets in CSV or Parquet
files and shows some or all differences. It uses the same underlying
functionality as the `tdda.referencetest` assertions such as
`assertDataFramesEqual`, and provides similar control over what
differences to consider, e.g. which fields, and strictness of type and
numeric comparisons. It also provides a number of options for controlling
the display of differences.

By default, comparisons are row-based and consider all fields (columns),
as typed values after reading.

### OPTIONS

`--fields` *FIELD1,FIELD2*,...  
  Check only these fields (comma-separated list)

`--xfields` *FIELD1,FIELD2*,...  
  Check all fields except these (comma-separated list)

`--horizontal`, `-H`,  
  Horizontal dispay (left and right, side by side)

`--vertical`, `-V`,  
  Vertical dispay (left above right)


`--find-md`  
  Attempt to find associated metadata for flat files.

`--no-md`, `--no-find-md`  
  Do not attempt to find associated metadata for flat files.

`--key` *FIELD*  
  Use this field as a join key when reporting differences.

`--maxdiffs` *N*  
  Maximum number of differences to show.


`--mono`  
  Show monochrome output with different values in bold and shared values
  dimmed.

`--bw`  
  Show black and white output with different values in bold and shared
  values in the terminal's default style.

`--colours`, `-c`, `--colours` *COLOURS*  
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
  e.g. --prefixes "actual:-ref:" or "actual: -ref: " to include spaces


`-N`, `--no-config`  
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


### EXAMPLES

Data suitable for all examples can be obtained with

`tdda examples diff`

1. tdda diff a.csv a.csv

This is the simplest form of the command. It will read a.csv and
convert it to a data frame, using the default back end (Pandas).

2. tdda diff a.csv b.csv --vertical

Compare two CSV files, stacking left and right values vertically
rather than side by side. Useful when there are many columns or
long values.

3. tdda diff before.parquet after.parquet --key Income,Expenditure

Compare two Parquet files using a composite join key. The fields
`Income` and `Expenditure` must form a primary key in both datasets.
Rows are matched by key rather than by position.

4. tdda diff actual.csv expected.csv --AE --bw

Compare two CSV files using `A:` and `E:` as markers for actual and
expected, with monochrome bold highlighting instead of colour.

5. tdda diff foo.csv: bar.csv:

Compare two CSV files, asking TDDA to find associated metadata files
for each using naming conventions (e.g. `@.serial` or `foo-metadata.json`
in the same directory).

6. tdda diff foo.csv bar.txt:money.serial

Compare `foo.csv` (loaded with default settings) against `bar.txt`,
using `money.serial` as the metadata file describing its format.

7. tdda diff a.parquet b.csv --loose --dps 3

Compare a Parquet file against a CSV file with loose type matching
and floating-point values compared to 3 decimal places.

---

## `tdda serial`


### NAME

`tdda serial`  - Converts, interrogates and creates serial metadata files.

### SYNOPSIS
```
tdda serial [FLAGS] inmetadata outmetadata  
tdda serial --to FMT [FLAGS] inmetadata outmetadata  

Converts metadata from one metadata format, in inpath,
to another, in outpath.

tdda serial [FLAGS] indata outmetadata

Creates metadata for in indata in outmetadata

tdda serial [FLAGS] inmetadata script.py

Creates Python code for reading a file in the format in inmetadata as
Python. Often, a reading library would be specified, e.g.

tdda serial a.serial a.py --to pd.r

which specifies that they Python script should use pandas.read_csv.


Supported formats FMT:

  SHORT FORM  LONG FORM/Description
  .         tdda.serial
  pd.r      pandas.read_csv
  pd.w      pandas.DataFrame.to_csv
  pl.r      polars.read_csv
  pl.w      polars.DataFrame.write_csv
  csv.r     python.csv.reader
  csv.w     python.csv.writer
  csvw      CSVW
  fl        frictionless
  fless     frictionless
  fl.r      frictionless.resource
  fl.p      frictionless.package

Multiple formats can be separated by commas.

Format is usually inferred from filename if following common conventions
for tdda.serial, CSVW, and frictionless.
```
### OPTIONS

`--to FMT`             Specify output metadata format (see list of formats above)

`-B BE, --backend BE`  Specify backend for Pandas flavours:
`n`: `numpy_nullable`
`a`: `pyarrow`
`o`: for original Pandas backend.

`--for FILE`            Filename for data to use when generating CSVW
or Frictionless data.
(Can also be used for `tdda.serial` and `.py` output)

`-N, --no-config`        Use default configuration (ignore ~/.tdda.toml)

`-g, --gen, --generate`  Generate (infer) metadata for flat file

`-q, --quiet`            Quiet output
`-v, --verbose`          Verbose output
`-V, --Verbose`          More verbose output

### Options used primarily or exclusively with `--generate`/`--gen`/`-g`

`--sep D, --delimiter D`     Specify `D` as the field separator.

`--quote-char Q, --quote Q`  Specify `Q` as the quote character.
                             (Q is always `"` or `'` in practice.)

`--nulls S`                  Specify null indicator, or comma-separated
                             list of null indicators.

`--escape`                   Use backslash as escape character.
                             **NOTE:** Always backslash: does not take argument.

`--no-escape`                Do not support backslash escaping with `-g`.
                             **NOTE:** This only affects quotes, separators,
                             and backslashes. Standard escapes for control
                             sequences (\t, \n, \t, \f) are always supported.

`--stutter`                  Specify quote stuttering.
                             Usually an alternative to `--escape`.

`--no-stutter`               Do not use quote stuttering.
                             Usually used with `--escape`.



`--encoding ENC, -e ENC`     Specify `ENC` as encoding.

`--date-format D`            Specify `D` as the (file-wide default) date format.

`--datetime-format D`        Specify `D` as the (file-wide default) format
                             for `datetime` fields.

`--sample-lines N, -n N`     Use (up to) `N` sample lines when inferring
                             metadata.

`--single-field, -1`         Inform the metadata inferred that the file
                             contains only a single field (column).

`--include-path`             Include `path` in `.serial` output

`--exclude-path`             Do not include in `.serial` output

`--quoting Q`                Set `quoting` to `Q`. Q must be one of:

                              * `QUOTE_ALL`
                              * `QUOTE_MINIMAL`
                              * `QUOTE_NONNUMERIC`
                              * `QUOTE_NONE`
                              * `QUOTE_NOTNULL`
                              * `QUOTE_STRINGS`
                              * `QUOTE_STRINGS_ONLY`

`--use-literal-dates`         Specifies that date formats should be written
                              to `.serial` files with unambiguous
                              literal examples such as `2000-12-31T12:34:56`.

`--use-yyyy-dates`            Specifies that date formats should be written
                              to `.serial` files in the form examplified
                              by `YYYY-MM-DD HH:MM:SS`.

`--use-pc-dates`              Specifies that date formats should be written
                              to `.serial` files in Python
                              `strftime`-compatible % formats, exemplified by
                              `%Y-%m-%dT%H:%M:%S`.

### EXAMPLES

`tdda serial a.csv a.serial`
   Generate tdda.serial metadata describing format of `a.csv` in `a.serial`.

`tdda serial --to . a.csv a.serial`
    Same as previous, expicitly specifying the default, `tdda.serial`,
    output format with `.`.

`tdda serial a.csv a-metadata.json`
    Generate CSVW metadata describing format of `a.csv` in `a-metadata.json`

`tdda serial --to csvw a.csv a.json`
    Same as previous, explicitly specifying format with non-standard output name

`tdda serial a.serial a-metadata.json`
    Generate Converts `tdda.metadata` metadata to CSVW

`tdda serial a-metadata.json a.serial`
    Generate Converts `tdda.metadata` metadata to CSVW

### USING SERIAL METADATA WITH TDDA COMMANDS

For all tdda command-line commands, and in most places within
API calls where CSV or other flat file is specified, there is the
option to specify the file format using `tdda.serial` files,
CSVW files, or Frictionless files. This is based on the `:` (colon) specifier.

When specifying a path to a CSV (or other flat) file:

 * If the path is used by itself, the `tdda` library will use
   either `tdda.serial.csv_to_pandas` or `tdda.serial.csv_to_polars`
   to read it into a DataFrame. The default is currently pandas
   (with the `numpy_nullable` back end), but this can be
   [configured](configuration.md)
   or, in many cases controlled with command line flags
   (`--polars`, `--pandas`, `--backend BACKEND` (for Pandas only)).

 * If the path ends in a colon (e.g. `foo.csv:`), TDDA will search
   for metadata in the same directory as the file and, if it finds
   one, pass that to the appropriate `csv_to_...` function for
   more accurate DataFrame generation.

 * In doing this, it will look for the following in priority order,
   given a file `foo.csv`:

     - `foo.csv.serial` (`tdda.serial` metadata)
     - `foo.serial` (`tdda.serial` metadata). This is actually more
       common than the previous form, but if there are multiple files
       with different extensions, the former is more specific, so is
       checked first.
     - Anything that matches foo using `@` as a wildcard, e.g.
       `@.serial`, `f@.serial`, `f@o.serial`, `@oo.serial`.
       (`@` acts like `*` in the shell, while avoiding needing
       `*` in filenames, which can be awkward.)
     - `foo-metadata.json`, `foo-csvmetadata.json`, `foo-csv-metadata.json`,
       `foo.csvmetadata.json`, `foo.csv-metadata.json`
       (all of which are common conventions for CSVW metadata files).
     - The same CSVW patterns with `@` wildcards
     - `foo.serial.json`, `foo.serial.yaml`, `foo.resource.json`,
       `foo.resource.yaml`, `foo.package.json`, `foo.package.yaml`,
       all of which are common for Frictionless metadata files.
     - The same patterns for `serial` or `package` frictionless files
       with `@` wildcards. Wildcards are not searched in `resource` files,
       because in frictionless these always correspond to a single
       data file.

 * If the path contains a colon, the part to the right of the colon
   will be interpreted as a metadata file. So `foo.csv:bar.serial`
   will use `bar.serial`.



### BUGS

The `tdda serial` functionality is fairly new, and there are probably
still many bugs an undesirable features in the implementation.

---

## `tdda gentest`


### NAME

`tdda gentest` - Gentest writes tests, so you don't have to.™

### SYNOPSIS
```
tdda gentest   Runs Wizard

tdda gentest   'SHELL COMMAND' [OPTIONS]
                 [test_output.py [reference files]]

```
### DESCRIPTION


### OPTIONS

  -h, --help            show this help message and exit
  -?, --?               Same as -h or --help
  -m, --max-files MAX_FILES
Max files to track
  -r, --relative-paths  Show relative paths wherever possible
  -n, --iterations ITERATIONS
Number of times to run the command (default 2)
  -O, --no-stdout       Do not generate a test checking output to STDOUT
  -E, --no-stderr       Do not generate a test checking output to STDERR
  -Z, --non-zero-exit   Do not require exit status to be 0
  -C, --no-clobber      Do not overwrite existing test script or reference directory
  -N, --no-config       Use default configuration (ignore ~/.tdda.toml)


### EXAMPLES

---

## `tdda tag`


### NAME

`tdda tag`  -- tag tests that failed in the last reference test run

### SYNOPSIS
```
tdda tag
```
### DESCRIPTION

The `tdda tag` command reads the log of failing tests written by the most
recent reference test run and adds `@tag` decorators to those tests in
their source files. Tagged tests can then be run in isolation, allowing
a rapid edit-test cycle focused on failing tests.

Before `tdda tag` can be used, tests must be run with failure logging
enabled, which writes the IDs of failing tests to a log file.

### WORKFLOW

A typical workflow with `unittest`-style tests (`ReferenceTestCase`) is:


`python tests.py -9      # Remove any existing @tag decorators`  
`python tests.py -F      # Run tests, logging failures`  
`tdda tag                # Add @tag to failing tests`  
`python tests.py -1      # Run only tagged (failing) tests`  


When all tests are passing:

`python tests.py -9      # Remove @tag decorators`  

The equivalent workflow with `pytest` is:

`pytest --untag          # Remove any existing @tag decorators`  
`pytest --log-failures   # Run tests, logging failures`  
`tdda tag                # Add @tag to failing tests`  
`pytest --tagged         # Run only tagged (failing) tests`  

When all tests are passing:

`pytest --untag          # Remove @tag decorators`

### SEE ALSO

tdda(1),
tdda-reftest(1),
tdda-reftest-unittest(1),
tdda-reftest-pytest(1)

---

## `tdda examples`


### NAME

`tdda` examples - Creates example data for TDDA

### SYNOPSIS
```
tdda examples [OUTDIR]
tdda examples [MODULE...] [OUTDIR]
tdda examples all [OUTDIR]
```
### POSITIONAL ARGUMENTS

*MODULE* can be any of:
  - referencetest
  - constraints
  - rexpy
  - gentest
  - book  
If not specified, all the first four will be used created, without
requiring internet access.

*OUTDIR* is an optional directory in which to write the example
directories; by default this will be the current working directory (.).

If `all` is specified, or `book` is included,
the `tdda-book-examples` will be downloaded from GitHub, which
does require internet access.


### DESCRIPTION

Write out example code and data for all examples, by default,
or for a particular module if specified.

If no module is specified, examples for all four are written out.

Examples are always created in subdirectories of the current directory `.`

### EXAMPLES

a. `tdda examples`
   Creates the referencetest, constraints, rexpy, and gentest
   examples in `.`

b. `tdda examples gentest`  
   Creates `examples_gentest` in `.`

c. `tdda examples gentest book`  
   Creates gentest and book examples in `.`

d. `tdda examples all`  
   Creates all the examples, four from local files and the book
   examples from GitHub in `.`

---

## `tdda version`

### NAME

`tdda version` - Reports the installed version of tdda

### SYNOPSIS
```
tdda version
```
### DESCRIPTION

Reports the version number of the installed TDDA tools.

### EXAMPLES

`tdda version`

---

## `tdda config`

### NAME

`tdda config` - Shows config settings

### SYNOPSIS
```
tdda config [--annotated|-a] [--current|-c] [--default|-d] [--file|-f]  
tdda config [--annotated|-a] current|default|file
```
### DESCRIPTION

Shows configuration information. Use:

`-c`, `--current`, or `current` for the current configuration  
`-d`, `--default`, or `default` for the default configuration  
`-f`, `--file`, or `file` for the configuration file location and contents.

With no argument, it shows the current configuration.

Use `-a` or `--annotated` with any of the above to show allowed values
alongside each parameter.

### EXAMPLES

`tdda config`  
`tdda config -c`  
`tdda config -d`  
`tdda config -f`


### PARAMETERS

#### `null_rep`
Used to show nulls in some contexts.  
**Default:** `"∅"`  
**Allowed:** Any string
#### `colour`
Controls whether output is colourized.  
**Default:** `true`  
**Allowed:** `true`, `false`
#### `engine`
Controls whether pandas or polars is used for CSV files by default.  
**Default:** `"pandas"`  
**Allowed:** `"pandas"`, `"polars"`
#### `pandas_backend`
Controls default backend for CSV loading etc.  
**Default:** `"numpy_nullable"`  
**Allowed:** `"numpy_nullable"` (or `"n"`), `"pyarrow"` (or `"a"`), `"original"` (or `"o"`)

### PARAMETERS (referencetest)

#### `left_colour`
Colour for left (actual) side of diffs.  
**Default:** `"red"`  
**Allowed:** A named ANSI colour (red, bright_red etc.) or an RGB hex colour with leading # such as #FF0000 for pure red. Interpreted by the rich library.
#### `right_colour`
Colour for right (expected) side of diffs.  
**Default:** `"green"`  
**Allowed:** A named ANSI colour (red, bright_red etc.) or an RGB hex colour with leading # such as #FF0000 for pure red. Interpreted by the rich library.
#### `failure_colour`
Colour used to highlight failures.  
**Default:** `"red"`  
**Allowed:** A named ANSI colour (red, bright_red etc.) or an RGB hex colour with leading # such as #FF0000 for pure red. Interpreted by the rich library.
#### `mono`
Use bold instead of colour for diffs.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `bw`
Black and white mode: no colour or bold.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `left_prefix`
Prefix string for left (actual) diff lines.  
**Default:** `"< "`  
**Allowed:** Any string
#### `right_prefix`
Prefix string for right (expected) diff lines.  
**Default:** `"> "`  
**Allowed:** Any string
#### `vertical`
Show diffs vertically rather than side by side.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `force_val_prefixes`
Always show left/right prefixes on diff lines.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `type_checking`
How strictly to check types in reference test comparisons.  
**Default:** `"strict"`  
**Allowed:** `"strict"`, `"medium"`, `"loose"`
#### `log_failures`
Log failing test IDs to file for use with tdda tag.  
**Default:** `false`  
**Allowed:** `true`, `false`

### PARAMETERS (constraints)

#### `interleave`
Interleave pass and fail results in verify output.  
**Default:** `true`  
**Allowed:** `true`, `false`
#### `per_constraint`
Report results per constraint rather than per field.  
**Default:** `true`  
**Allowed:** `true`, `false`
#### `detect_passes`
Include passing fields in detect output.  
**Default:** `true`  
**Allowed:** `true`, `false`
#### `report_formats`
List of additional report formats to generate.  
**Default:** `[]`  
**Allowed:** Any subset of `"html"`, `"md"`, `"txt"`, `"json"`, `"yaml"`, `"toml"`
#### `write_all_records`
Write all records to detect output, not just failures.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `int_bools`
Use integers (0/1) rather than booleans in detect output.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `verify_required_fields`
Verify that all required fields are present.  
**Default:** unset  
**Allowed:** `true`, `false`
#### `verify_allowed_fields`
Verify that no fields are present outside the allowed set.  
**Default:** unset  
**Allowed:** `true`, `false`
#### `write_required_fields`
Discover should include the required-fields constraint.  
**Default:** `false`  
**Allowed:** `true`, `false`
#### `write_allowed_fields`
Discover should include an allowed-fields constraint.  
**Default:** `false`  
**Allowed:** `true`, `false`

### PARAMETERS (tddadiff)

#### `type_checking`
How strictly to check types when comparing dataframes.  
**Default:** `"medium"`  
**Allowed:** `"strict"`, `"medium"`, `"loose"`
#### `find_md`
Infer metadata when comparing dataframes with tdda diff.  
**Default:** `true`  
**Allowed:** `true`, `false`

### PARAMETERS (serial)

#### `md_inpath`
Path(s) to search for serial metadata files; relative paths are resolved relative to the CSV file.  
**Default:** `"./_write.serial"`

---

## `tdda test`


### NAME

`tdda test`  -- Run the tdda libraries tests 

### SYNOPSIS
```
tdda test
```
### DESCRIPTION

Runs tdda's (internal) tests.

**NOTE:** It is hard to guarantee that all will pass on all systems
given that dependencies are not tightly pinned. It is not necessarily
a problem if some tests fail, but is a concern if a very large number
fail.

### SEE ALSO

tdda(1),

---

## `tdda help`


### NAME

`tdda help` - Provides help on `tdda` and its sub-commands.

### SYNOPSIS
```
tdda help
tdda help COMMAND
```
### POSITIONAL ARGUMENTS

*COMMAND* can be any of:

 - `discover`
 - `verify`
 - `detect`

 - `gentest`
 - `diff`
 - `tag`
 - `serial`
 - `examples`

 - `config`
 - `help`
 - `version`
 - `test`

### DESCRIPTION

Shows help on a tdda subcommand or topic.

Taking inspiration from `git`, if the man pages are installed,
help on main commands can be obtained with

   `man tdda-COMMAND`

For example:

   `man tdda-discover`

Help can also be obtained on each command with `--help`, `-h` or `-?`, e.g.

   `tdda discover --help`

###  EXAMPLES

`tdda help`               Shows this help

`tdda help gentest`       Shows help on gentest

---

## `rexpy`


### NAME

`rexpy` -- infer regular expressions from example strings

### SYNOPSIS
```
rexpy [FLAGS] [INPUTFILE [OUTPUTFILE]]
```
### DESCRIPTION

`rexpy` reads a list of strings (one per line) and infers one or more
regular expressions that characterize them.

If *INPUTFILE* is provided it should contain one string per line;
otherwise lines are read from standard input.

If *OUTPUTFILE* is provided, the regular expressions found will be
written there (one per line); otherwise they will be printed to
standard output.

### OPTIONS

`-h`, `--header`  
  Discard the first line as a header.

`-?`, `--help`  
  Print usage information and exit.

`-g`, `--group`  
  Generate capture groups for each variable fragment of each regular
  expression, i.e. surround variable components with parentheses.  
  e.g.    `    ^[A-Z]+\-[0-9]+$`  
  becomes `^([A-Z]+)\-([0-9]+)$`

`-q`, `--quote`  
  Display regular expressions as double-quoted, escaped strings,
  suitable for use in Unix shells, JSON, and string literals in many
  programming languages.  
  e.g.    `    ^[A-Z]+\-[0-9]+$`  
  becomes `"^[A-Z]+\-[0-9]+$"`

`--portable`, `--grep`  
  Produce maximally portable regular expressions
  (e.g. `[0-9]` rather than `\d`). This is the default.

`--java`  
  Produce Java-style regular expressions (e.g. `\p{Digit}`).

`--posix`  
  Produce POSIX-compliant regular expressions
  (e.g. `[[:digit:]]` rather than `\d`).

`--perl`  
  Produce Perl-style regular expressions (e.g. `\d`).

`-u`, `--underscore`  
  Allow underscore to be treated as a letter.
  Mostly useful for matching identifiers. Also `-_`.

`-d`, `--dot`, `--period`  
  Allow dot to be treated as a letter.
  Mostly useful for matching identifiers. Also `-.`.

`-m`, `--minus`, `--hyphen`, `--dash`  
  Allow minus to be treated as a letter.
  Mostly useful for matching identifiers.

`-vlf`, `--variable`  
  Use variable-length fragments.

`-flf`, `--fixed`  
  Use fixed-length fragments.

`-v`, `--version`  
  Print the version number.

`-V`, `--verbose`  
  Set verbosity level to 1.

`-VV`, `--Verbose`  
  Set verbosity level to 2.

### SEE ALSO

tdda(1),
tdda-discover(1)
