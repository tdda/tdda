# Data Validation with Constraints

The TDDA library provides support for constraint generation,
data validation (verification) and anomaly detection for datasets,
including `.csv` and other flat files, Parquet files, and Pandas DataFrames.
(Support for Polars dataframes is planned; most of the rest of
`tdda` already supports Polars)

The module includes:

* The [`tdda`](cli.md#tdda) command-line tool for discovering constraints in data,
  and for verifying data against those constraints,
  using the [TDDA JSON file format](#tdda_json_file_format) (`.tdda` files).
* A Python `tdda.constraints` library containing classes that
  implement constraint discovery and validation, for use from within
  other Python programs.
* Python implementations of constraint discovery, data validation
  (verification),
  and anomaly detection for a number of data sources:

  - `.csv` and other flat files
  - Pandas and R DataFrames saved as `.parquet` files
  - PostgreSQL database tables (`postgres:`)
  - MySQL database tables (`mysql:`)
  - SQLite database tables (`sqlite:`)
  - MongoDB document collections (`mongodb:`; partial support)

:::{note}
To use databases, you may need
to install extra optional packages.
See {ref}`optional_installations`.
:::

For a much more detailed tutorial introduction on using TDDA for
data validation, read chapter 1-7 of [the book](https://book.tdda.info).


(tdda_command_line_tool)=

## The `tdda` Command-line Tool

The [`tdda`](cli.md#tdda) command-line utility provides a tool for discovering constraints
in data and saving them as a `.tdda` file in the
[TDDA JSON file format](#tdda_json_file_format), and also for verifying data against constraints stored in a `.tdda` file.

It also provides some other functionality to help with using the tool.
The following command forms are supported for data validation:

* [`tdda discover`](#tdda_discover_tool) — perform constraint discovery.
* [`tdda verify`](cli.md#tdda-verify) — verify data against constraints.
* [`tdda detect`](cli.md#tdda-detect) — detect anomalies in data by checking constraints.
* [`tdda examples`](cli.md#tdda-examples) — generate example data and code.

See {ref}`examples` for more detail on the code and data
examples that are included as part of the `tdda` package.

See {ref}`tests` for more detail on the `tdda` package's own tests,
used to test that the package is installed and configured correctly.


(tdda_discover_tool)=

## `tdda discover`

The `tdda discover` command can generate constraints for data,
and save the generated constraints as a
[TDDA JSON file format](#tdda_json_file_format) file (`.tdda`).

**Usage:**

```none
tdda discover [FLAGS] input [constraints.tdda]
```

* `input` is one of:

  - a `.csv` file or other flat file
    (which can have
    [associated metadata](serialformat.md#tdda-serial-colon-format))
  - a `-`, meaning that a `.csv` file should be read from standard input
  - a `parquet` file containing a DataFrame, with extension
    `.parquet`
  - a database table

* `constraints.tdda`, if provided, specifies the name of a file to
  which the generated constraints will be written.

If no constraints output file is provided, or if `-` is used,
the constraints are written to standard output (`stdout`).

Optional flags include:

- `-r` or `--rex`, to include regular expression generation
- `-R` or `--norex`, to exclude regular expression generation

See [Constraints for CSV Files and Pandas DataFrames](#tdda_csv_file)
for details of how a `.csv` file is read.

See [Constraints for Databases](#tdda_db_table)
for details of how database tables are accessed.

See the [`tdda discover` man page](cli.md#tdda-discover) for more details
on options.


(tdda_verify_tool)=

## `tdda verify`

The `tdda verify` command is used to validate data from various sources,
against constraints from a
[TDDA JSON file format](#tdda_json_file_format) constraints file.

**Usage:**

```none
tdda verify [FLAGS] input [constraints.tdda]
```

* `input` is one of:

  - a flat file (e.g. `.csv`), which can have
    [associated metadata](serialformat.md#tdda-serial-colon-format)
  - a `-`, meaning it will read a flat file from standard input
  - a `parquet` file containing a DataFrame, with extension
    `.parquet`
  - a database table

* `constraints.tdda`, if provided, is a JSON `.tdda` file
  containing constraints.

If no constraints file is provided and the input is a flat file,
a constraints file with the same path as the input file, but with a `.tdda`
extension, will be used.

For database tables, the constraints file parameter is mandatory.

Optional flags include:

* `-a`, `--all`  
  Report all fields, even if there are no failures
* `-f`, `--fields`  
  Report only fields with failures
* `-7`, `--ascii`  
  Report in ASCII form, without using special characters.
* `--epsilon E`  
  Use this value of epsilon for fuzziness in comparing numeric values.
* `--type_checking strict|sloppy`  
  By default, type checking is *sloppy*, meaning that when checking type
  constraints, all numeric types are considered to be equivalent. With
  strict typing, `int` is considered different from `real`.

See [Constraints for CSV Files and Pandas DataFrames](#tdda_csv_file)
for details of how a flat file is read.

See [Constraints for Databases](#tdda_db_table)
for details of how database tables are accessed.

See the [`tdda verify` man page](cli.md#tdda-verify)
for more details on options.


(tdda_detect_tool)=

## `tdda detect`

The `tdda detect` command is used to detect anomalies on data,
by checking against constraints from a
[TDDA JSON file format](#tdda_json_file_format) constraints file.

**Usage:**

```none
tdda detect [FLAGS] input constraints.tdda output
```

* `input` is one of:

  - a flat file (e.g. `.csv`), which can have
    [associated metadata](serialformat.md#tdda-serial-colon-format)
  - a `-`, meaning it will read a flat file from standard input
  - a `parquet` file containing a DataFrame, with extension
    `.parquet`
  - a database table

* `constraints.tdda`, is a JSON `.tdda` file containing constraints.

* `output` is one of:

  - a `.csv` file to be created containing failing records
  - a `-`, meaning it will write the `.csv` file containing
    failing records to standard output
  - a `parquet` file with extension `.parquet`, to be created
    containing a DataFrame of failing records

If no constraints file is provided and the input is a flat file,
a constraints file with the same path as the input file, but with a `.tdda`
extension, will be used.

Optional flags include:

* `-a`, `--all`  
  Report all fields, even if there are no failures
* `-f`, `--fields`  
  Report only fields with failures
* `-7`, `--ascii`  
  Report in ASCII form, without using special characters.
* `--epsilon E`  
  Use this value of epsilon for fuzziness in comparing numeric values.
* `--type_checking strict|sloppy`  
  By default, type-checking is sloppy, meaning that when checking type
  constraints, all numeric types are considered to be equivalent. With
  strict typing, `int` is considered different from `real`.
* `--write-all`  
  Include passing records in the output.
* `--per-constraint`  
  Write one column per failing constraint, as well as the `n_failures`
  total column for each row.
* `--output-fields FIELD1 FIELD2 ...`  
  Specify original columns to write out. If used with no field names,
  all original columns will be included.
* `--index`  
  Include a row-number index in the output file. The row number is
  automatically included if no output fields are specified. Rows are
  usually numbered from 1, unless the (parquet) input file already has
  an index.

If no records fail any of the constraints, then no output file is
created (and if the output file already exists, it is deleted).

See [Constraints for CSV Files and Pandas DataFrames](#tdda_csv_file)
for details of how a flat file is read.

See [Constraints for Databases](#tdda_db_table)
for details of how database tables are accessed.

See the [`tdda detect` man page](cli.md#tdda-detect) for more details
on options.

(tdda_csv_file)=

## Constraints for CSV Files and Pandas DataFrames

If a flat file (`.csv` or other) is used with the [`tdda`](cli.md#tdda)
command-line tool, it will by default be processed by the standard Pandas
`.csv` file reader with the following settings:

* `index_col` is `None`
* `infer_datetime_format` is `True`
* `quotechar` is `"`
* `quoting` is `csv.QUOTE_MINIMAL`
* `escapechar` is `\` (backslash)
* `na_values` are the empty string, `"NaN"`, and `"NULL"`
* `keep_default_na` is `False`

The [`tdda.serial` colon format](serialformat.md#tdda-serial-colon-format)
can be used to supply metadata describing the flat file, allowing more
accurate reading (types, separators, encodings, and so on).


(tdda_db_table)=

## Constraints for Databases

When a database table is used with any [`tdda`](cli.md#tdda) command-line tool,
the table name (including an optional schema) can be preceded by
`DBTYPE` chosen from `postgres`, `mysql`, `sqlite` or
`mongodb`:

```
DBTYPE:[schema.]tablename
```

The following example will use the file `.tdda_db_conn_postgres` from your
home directory (see [Database Connection Files](#tdda_db_conn)), providing
all of the default parameters for the database connection.

```
tdda discover postgres:mytable
tdda discover postgres:myschema.mytable
```

For MongoDB, document collections are used instead
of database tables, and a document can be referred to at any level in
the collection structure. Only scalar properties are used for constraint
discovery and verification (and any deeper nested structure is ignored).
For example:

```
tdda discover mongodb:mydocument
tdda discover mongodb:subcollection.mysubdocument
```


Parameters can also be provided using the following flags (which override
the values in the `.tdda_db_conn_DBTYPE` file, if provided):

* `--conn FILE`  
  Database connection file (see [Database Connection Files](#tdda_db_conn))
* `--dbtype DBTYPE`  
  Type of database
* `--db DATABASE`  
  Name of database to connect to
* `--host HOSTNAME`  
  Name of server to connect to
* `--port PORTNUMBER`  
  IP port number to connect to
* `--user USERNAME`  
  Username to connect as
* `--password PASSWORD`  
  Password to authenticate with

If `--conn` is provided, then none of the other options are required, and
the database connection details are read from the specified file.

If the database type is specified (with the `--dbtype` option, or by
prefixing the table name, such as `postgres:mytable`), then a default
connection file `.tdda_db_conn_DBTYPE` (in your home directory) is used,
if present (where `DBTYPE` is the name of the kind of database server).

To use constraints for databases, you must have an appropriate
DB-API (PEP-0249) driver library installed within your Python environment.

These are:

* For PostgreSQL: `pygresql` or `PyGreSQL`

* For MySQL: `MySQL-python`, `mysqlclient` or `mysql-connector-python`

* For SQLite: `sqlite3`

* For MongoDB: `pymongo`


(tdda_db_conn)=

### Database Connection Files

To use a database source, you can either specify the database type
using the `--dbtype DBTYPE` option, or you can prefix the table name
with an appropriate `DBTYPE:` (one of the supported kinds of database
server, such as `postgres`).

You can provide default values for all of the other database options in
a database connection file `.tdda_db_conn_DBTYPE`, in your home directory.

Any database-related options passed in on the command line will
override the default settings from the connection file.

A `tdda_db_conn_DBTYPE` file is a JSON file of the form:

```
{
    "dbtype": DBTYPE,
    "db": DATABASE,
    "host": HOSTNAME,
    "port": PORTNUMBER,
    "user": USERNAME,
    "password": PASSWORD,
    "schema": SCHEMA,
}
```

Some additional notes:

* All the entries are optional.

* If a `password` is provided, then care should be taken to ensure that the
  file has appropriate filesystem permissions so that it cannot be read by
  other users.

* If a `schema` is provided, then it will be used as the default schema,
  when constraints are discovered or verified on a table name with no
  schema specified.

* For MySQL (in a `.tdda_db_conn_mysql` file), the `schema`
  parameter **must** be specified, as there is no built-in default for it to
  use.

* For Microsoft Windows, the connector file should have the
  same name as for Unix, beginning with a dot, even though this form of
  filename is not otherwise commonly used on Windows.


(tdda_json_file_format)=

## TDDA JSON file format

A `.tdda` file is a JSON file containing a single JSON object of the form:

```
{
    "fields": {
        field-name: field-constraints,
        ...
    }
}
```

Each `field-constraints` item is a JSON object containing a property for
each included constraint:

```
{
    "type": one of int, real, bool, string or date
    "min": minimum allowed value,
    "max": maximum allowed value,
    "min_length": minimum allowed string length (for string fields),
    "max_length": maximum allowed string length (for string fields),
    "max_nulls": maximum number of null values allowed,
    "sign": one of positive, negative, non-positive, non-negative,
    "no_duplicates": true if the field values must be unique,
    "values": list of distinct allowed values,
    "rex": list of regular expressions, to cover all cases
}
```

It may also include a dataset section with
`allowed_fields` or `required_fields`, or both.
By default, this looks like this:

```json
"dataset": {
    "allowed_fields": [],
    "required_fields": [
        "*"
    ]
}
```

The `allowed_fields` section is a list of fields
that are allowed to be present in the dataset to be validated,
in addition to those listed in the `fields` section.
(It makes no sense not to allow fields with constraints
in data, so those are implicitly allowed.)
The wildcards `*` (for any substring) and `?` (for any single character)
are allowed, so it would be possible to use

```json
"allowed_fields": ["checksum", "sha*"]
```

to allow `checksum` and any field starting `sha` in the validation
data, or `"allowed_fields": "*"` (or `["*"]`) to allow any extra fields.

The `required_fields` section specifies fields that must be present
in the data that is checked. It can also use wildcards, but these
now operate only over the fields listed. The default value `["*"]`
means that all listed fields are required. If only a subset are required,
they can be listed explicitly or using wildcards. So

```json
"required_fields": ["checksum", "sha*"]
```

would mean that the `checksum` field (which should be among those
in the `fields` section) and any fields in the `fields` section starting
`sha` are required in data when it is validated.


(constraint_examples)=

## Constraints Examples

```{eval-rst}
.. automodule:: tdda.constraints.examples
   :members:
```
