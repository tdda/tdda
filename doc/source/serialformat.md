# `tdda.serial`: Metadata and Tools for Flat (“CSV”) Files

A `.serial` file (also known as a `tdda.serial` file)
is a JSON file describing the format of one or more
flat (“CSV”) files. It is the primary metadata format
used by the `tdda` library, which includes various tools
for working with `.serial` metadatain the `tdda.serial` module.
The primary goal of `tdda.serial` is allow data in flat files to be read
more accurately and to serve as documentation of how data
has been written to flat files.

The current main features of `tdda.serial` are:

 * A file format for describing key aspects of CSV and other “flat” files,
   including things like separators, quoting, escaping and nulls,
   together with field names, types, and formats.
 * Facilities for using `.serial` files when reading and writing flat files
   with (currently) Pandas and Polars in Python
   (`csv_to_pandas`, `csv_to_polars`, `pandas_to_csv`, `polars_to_csv`,
   as well as tools for generating keyword arguments for `read_csv`
   functions and Python code for reading flat files based on a metadata
   specification).
 * Tools allowing conversion between `tdda.serial` files and other metadata
   formats---currently [CSVW](https://csvw.org)
   and [Frictionless](https://frictionlessdata.io).
 * Facilities for generating inferred `tdda.serial` files from
   a flat file.
 * A command-line interface for most of the above functionality
   (`tdda serial`).
 * The ability for various tdda tools to be guided by a
   `tdda.serial` files when reading flat files for things like
   constraint generation, data validation, and dataset comparison
   with `tdda diff`. (In general, this can be achieved by using
   either `foo.csv:` as a filename specifier, which tells `tdda`
   to look for metadata based on filename conventions,
   or `foo.csv:md.serial` to use metadata in `md.serial`.)

A single `.serial` file can describe a format shared by many concrete
flat files, unlike CSVW, which is primarily concerned with describing
specific named files. In this respect, it is more similar to a
Frictionless schema, as opposed to a Frictionless resource or package.
A `.serial` file can also contain library-specific sections (for
`pandas.read_csv`, `polars.read_csv` etc.) alongside or instead of the
`tdda.serial` section.

In general, it is preferable to use the `tdda.serial` section;
the other sections are intended primarily for cases in which:
 - Something is not capable of being expressed in `tdda.serial`;
 - The intention is only to use a single library for reading/writing,
   and higher fidelity may be guaranteed by using a custom section.


## The `tdda.serial` File Structure

A `.serial` file is a JSON object with the following top-level keys:

```json
{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-3.0.0",
    "tdda.serial": { ... },
    "pandas.read_csv": { ... },
    "pandas.DataFrame.to_csv": { ... },
    "polars.read_csv": { ... },
    "polars.DataFrame.write_csv": { ... },
    "python.csv.reader": { ... },
    "python.csv.writer": { ... }
}
```

In fact, any key may be used for a custom format specification
for some flat-file reader or writer.

### Top-level Keys

**`format`** *(string, required)*
: Must be `"http://tdda.info/ns/tdda.serial"`. Identifies the file as
  a `tdda.serial` file. In future, this string may include numbered
  versions of tdda.serial.

**`writer`** *(string, optional)*
: The name and version of the software that wrote the file,
  e.g. `"tdda.serial-3.0.0"`.

**`tdda.serial`** *(object, optional)*
: The primary metadata section, described in detail below.

**`pandas.read_csv`**, **`pandas.DataFrame.to_csv`** *(objects, optional)*
: Library-specific sections containing keyword arguments for the
  corresponding Pandas functions, stored verbatim.

**`polars.read_csv`**, **`polars.DataFrame.write_csv`** *(objects, optional)*
: Library-specific sections containing keyword arguments for the
  corresponding Polars functions, stored verbatim.

**`python.csv.reader`**, **`python.csv.writer`** *(objects, optional)*
: Library-specific sections for the Python standard library `csv` module.

When multiple sections are present, the `tdda.serial` library chooses
which to use based on a preference order (typically `tdda.serial`
first, then library-specific sections). A preferred section can also
be specified explicitly with both the API and the command-line tools.


### Example

%% docdata/example.serial
```
{
    "format": "http://tdda.info/ns/tdda.serial",
    "tdda.serial": {
        "encoding": "UTF-8",
        "delimiter": "|",
        "quote_char": "\"",
        "escape_char": "\\",
        "stutter_quotes": false,
        "null_indicator": "",
        "date_format": "YYYY-MM-DD",
        "datetime_format": "DD/MM/YYYY HH:MM:SS",
        "header_row_count": 1,
        "header_row": 0,
        "fields": [
            {
                "name": "id",
                "fieldtype": "int"
            },
            {
                "name": "name",
                "fieldtype": "string"
            },
            {
                "name": "joined",
                "fieldtype": "date"
            },
            {
                "name": "last_seen",
                "fieldtype": "datetime",
                "format": "MM/DD/YYYY HH:MM:SS"
            }
        ]
    }
}
```


### The `tdda.serial` Section

This section contains a dataset-level description of the flat file
format, with optional per-field overrides.

#### Dataset-level Keys

All dataset-level keys are optional.

**`encoding`** *(string)*
: The text encoding of the file. Any Python codec name is accepted,
  e.g. `"UTF-8"`, `"latin-1"`.
  (Suggested default: `"UTF-8"`.)

**`delimiter`** *(string)*
: The field separator character. (Suggested default: `","`.)

**`quote_char`** *(string)*
: The character used to quote fields string data or, in some cases,
  other data, especially data that contains the delimiter or
  the field separator.
  Almost always double quote or single quote.
  (Suggested default: `"`, written as `"\""` in JSON.)

**`escape_char`** *(string)*
: When this is set to backslash (the only value it is likely to take,
  written as `"\\"` in JSON)
  this means that quote characters in quoted strings are escaped
  with backslash `"like \"this\" example"`. Backslash also escapes itself,
  and may be used to escape separators, whether quoted or not.
  It has no significance for common control escapes, which
  may appear as `\n`, `\r`, `\t`, `\f` in files regardless
  of this setting.
  Overescaping is common (escaping characters that don't
  need to be escaped in context) and this setting has no
  particular bearing on the cases. Most readers simply remove
  unnecessary escape characters.
  (Suggested default: `"\\"`.)

**`stutter_quotes`** *(boolean)*
: If `true`, the quote character is escaped by doubling it,
  `"like ""this"" example"`.
  If `false`, the escape character is used to escape embedded quotes.
  `"""this"""` would be used to represent the word *this* in double
  quotes when stutter is `true`.
  (Suggested default: `false`.)

**`null_indicator`** *(string or array of strings)*
: The string or strings used to represent null/missing values.
  (Suggested Default: empty string, written as `""` in JSON.)

**`date_format`** *(string)*
: The default format for `date` fields that have no per-field
  `format`. Also used as the fallback for `datetime` fields if
  `datetime_format` is not set. Accepts named formats (see
  [Date and Datetime Formats](#date-and-datetime-formats)) and Python
  `strftime` strings. (Suggested default: `"iso8601-date"`.)

**`datetime_format`** *(string)*
: The default format for `datetime` fields that have no per-field
  `format`. If not set, `date_format` is used as the fallback.
  Accepts named formats or Python `strftime` strings.

**`header_row_count`** *(integer)*
: The number of header rows at the top of the file. Default: `1`.

**`header_row`** *(integer)*
: The zero-based index of the row containing column names, within the
  header rows. Default: `0`.

**`accept_percentages_as_floats`** *(boolean)*
: If `true`, values like `"12.5%"` are read as `0.125`.
  (Suggested default: `false`.)

**`map_missing_trailing_cols_to_null`** *(boolean)*
: If `true`, rows with fewer fields than expected (as Excel sometimes
  produces) have missing trailing fields treated as null.
  (Suggested default: `false`.)

**`decimal_point`** *(string)*
: The character used as the decimal point in numeric fields.
  (Suggested default:  `"."`).

**`thou_sep`** *(string)*
: The thousands separator character in numeric fields, e.g. `","`.
  Optional; no suggested default.

**`true_values`** *(string or array of strings)*
: String values to interpret as *true* for boolean fields, in addition
  to the library defaults. Applies to all `bool` fields unless
  overridden for a given field.

**`false_values`** *(string or array of strings)*
: String values to interpret as *false* for boolean fields, in addition
  to the library defaults. Applies to all `bool` fields unless
  overridden for a given field.

**`quoting`** *string*
: Specifies which values are quoted
  There is little consistency about which values are quoted in flat files.
  Python's `csv` module defines constants for various options, but fail
  to include one of the most important. The `tdda.serial` format allows
  quoting to be set to any of the values supported by Python `csv` and
  also to one other common scheme. The values from Python'as `csv` library
  are:

  - `QUOTE_ALL`: all values are quoted.
  - `QUOTE_MINIMAL`: Only values that contain special characters.
    such as the field delimiter, or literal newlines.
  - `QUOTE_NONNUMERIC`: All non-numeric values (including nulls) are quored.
  - `QUOTE_NONE`: No values are quoted (escape is used for special
    characters).
  - `QUOTE_NOTNULL`: All non-null values are quoted (including numbers)
  - `QUOTE_STRINGS`: This is the same as QUOTE_NONUMERIC except that
    null values are not quoted.

The extra value supported by `tdda.serial` is

  - `QUOTE_STRINGS_ONLY`: Only string values are quoted: nulls and values
    of all non-string types are not quoted. (This is essentially what
    JSON does, except that JSON has no date/datetime types, so those are
    usually stored as strings, and therefore quoted.)

Optional. No default.

**`path`** *(string)*
: Optional path to a datafile. Not usually populated since `.serial`
  data usually applies to a set of datafiles rather than a single one.
  Can be relative or absolute. The path should be considered advisory
  rather than definitive, i.e. there is no problem at all to use
  a `.serial` file specifying a particular flat file with a different
  flat file. Indeed, this is common.
  Note: since `path` is only really for information, it can be set
  to a glob (wildcard) pattern like '*.csv' or 'foo*.csv' to indicate
  a set of files. `@` can also be used as the wildcard
  to match `tdda.serial` filename conventions (see below).

**`fields`** *(array or object)*
: Descriptions of the fields in the file. See
  [The `fields` Entry](#the-fields-entry).


#### The `fields` Entry

Fields can be specified as either an **array** or an **object
(dictionary)**.

**Array form** — the field list is taken to be complete and ordered.
Fields appear in the order they occur in the file. Each entry is a
field object (described below).

```json
"fields": [
    {"name": "id", "fieldtype": "int"},
    {"name": "date", "fieldtype": "date"}
]
```

**Object (dictionary) form** — the keys are the names of the fields
*as they appear in the file* (the external names), and the values are
field objects. This form is used for partial specifications, where only
some fields are described, and/or where internal names differ from
external names. Fields may appear in any order, and additional fields
in the file are permitted.

```json
"fields": {
    "commission date": {"name": "DateOfCommission", "fieldtype": "date"},
    "qa passed?":      {"name": "PassedQA", "fieldtype": "bool",
                        "true_values": "yes", "false_values": "no"}
}
```

**NOTE (field sortedness):**
JSON Objects (dictionaries) are formally unordered, i.e. the
order in which the entries appear has no semantic significance.
The object form is preferred when a `.serial` file is not making a
claim about the order of fields in a flat file. Despite this,
all recent versions of Python read JSON objects into Python dictionaries
preserving key order. The `tdda.serial` library always preserves order
when reading and writing serial files, so in practice the order in the
`.serial` file will always match the order in the flat file
if `tdda.serial` is used to generate the `.serial` file.

Conversely, in the rare cases that data is written without a header,
the table form is preferred because this unambiguously specifies field
order. In practice, the object/dictionary form will also work provided
the `.serial` has the field entries in the same order as the data file.


#### Field Keys

**`name`** *(string, required in array form)*
: The internal name for the field — the column name used in the
  resulting dataframe. In array form this is mandatory. In object form
  it can be omitted if the internal name is the same as the external
  (dictionary key) name. This is useful if there is a desire to replace
  some or all of the names used in the flat file with more convenient
  ones during processing.

**`fieldtype`** *(string)*
: The type of the field, from the table below.

| Value          | Description                              |
|:---------------|:-----------------------------------------|
| `bool`         | Boolean                                  |
| `int`          | Integer                                  |
| `float`        | Floating-point                           |
| `number`       | Unspecified numeric (integer or float)   |
| `string`       | Text                                     |
| `date`         | Date (no time component)                 |
| `datetime`     | Date and time                            |
| `datetime_tz`  | Date and time with timezone              |
| `time`         | Time only                                |
| `iso8601`      | ISO 8601 date or datetime (unspecified)  |

**`csvname`** *(string)*
: The name of the column in the file, if different from `name`. Used
  in array form when the file's column name differs from the desired
  internal name.

**`format`** *(string)*
: For `date` and `datetime` fields: the format of the date or datetime
  values in this field. Overrides `date_format` / `datetime_format`.
  Accepts named formats or Python `strftime` strings (see
  [Date and Datetime Formats](#date-and-datetime-formats)).

  For `bool` fields: a boolean format specification (e.g. `"yes|no"`).

**`null_indicator`** *(string or array of strings)*
: Null indicator(s) for this field, overriding the dataset-level
  `null_indicator`.

**`true_values`** *(string or array of strings)*
: True value(s) for this `bool` field, overriding the dataset-level
  `true_values`.

**`false_values`** *(string or array of strings)*
: False value(s) for this `bool` field, overriding the dataset-level
  `false_values`.

**`description`** *(string)*
: A human-readable description of the field.


### TDDA Serial Date and Datetime Formats

1. ISO8601

ISO8601 is the most widely understood, unproblematical format for
dates and times and is recommended for new data and date written.

This can be specified in tdda serial as follows.

 - `iso8601-date` can be used for ISO8601 dates (2000-12-31)
 - `iso8601-datetime` can be used for ISO8601 datetimes (2000-12-31T12:34:56)
 - `iso8601-datetime-tz` can be used for ISO8601 datetimes with timezone
    (2000-12-31T12:34:56+00:00) etc.
 - `iso8601` can be used to indicate “any of the above”.

With the ISO8601 variants, reading is liberal, allowing some
variation in separators, whereas writing is strict.


The `tdda.serial` format allows date formats to be specified in three
other ways:

2. Dates can specified using:

    - YYYY for four-digit years
    - YY for two-digit years
    - MM for *numeric* month
    - DD for day
    - HH for hour
    - MM for minute (Same as month! That's OK. Context disambiguates.)
    - MON for a spelt-out three letter month line Jan
    - MONTH for a spelt-out full month line January
    - SS for whole seconds
    - SS.S, SS.SS etc. (any number of S's after period) for fractional seconds.
    - +ZZ:ZZ or +ZZZZ for timezone. (Can use `-` instead of `+`)
    - AM or PM for 12-hour clock AM/PM indicator

   Any case may be used. MM for minutes and month is disambiguated
   by saying that MM when adjacent to YY or DD (other than a separator)
   is a month,
   and when adjacent to SS or HH indicates minutes.

   For example:

    - `YYYY-MM-DDTHH:MM:SS.S+ZZ:ZZ`
    - `YYYY-MM-DDTHH:MM:SS.S-ZZ:ZZ`
    - `YYYY-MM-DD HH:MM:SS+ZZZZ`
    - `YYYY-MM-DDTHH:MM:SS`
    - `YYYY-MM-DD HH:MM`
    - `YYYY-MM-DD`
    - `YY-MM-DD`
    - `YY-MM-DDTHH:MM:SS.SPM`
    - `YY-MM-DDTHH:MM:SSAM`
    - `DD/MM/YYYY HH:MM:SS`
    - `MM/DD/YYYY HH:MM:SS`
    - `MM.DD.YY HH:MM:SSAM`

The string will always be standarized to upper case on write, but is
case insensitive on read, for `.serial` files. (For `CSVW` files,
mixed case is used, followings CSVW's conventions).

3. Any **unambigous** date or datetime in the specified format
   can be used as a specifier. By unambigous, we mean:
    - The day is at least 13
    - The year is either four digits or 60 or greater or 00
   So

    - ` 2000-12-31T12:34:56.789+0000`
    - ` 31/12/2000T12:34:56.789+00:00`
    - ` 31-12-2000T12:34:56.789-0000`
    - ` 31.12.2000T12:34:56-00:00`
    - ` 31/12/2000T12:34:56`
    - ` 31/12/2000 12:34:56`
    - ` 31/12/2000`
    - ` 12/31/2000`
    - ` 12/31/00`
    - ` 31/12/00`
    - ` 31 Dec 2000`
    - ` 31 December 2000`
    - ` Dec 31 00`
    - ` 2000-12-31T12:34:56.789AM`
    - ` 2000-12-31T12:34:56.789PM`

   etc. are all acceptable. Things like

    - ` 2000-02-01T12:34:56.789+0000`
    - ` 01/02/2000T12:34:56.789+00:00`
    - ` 01-02-2000T12:34:56.789+0000`
    - ` 01.02.2000T12:34:56+0000`
    - ` 01/02/2000T12:34:56`
    - ` 01/02/2000 12:34:56`
    - ` 01/02/2000`
    - ` 02/01/2000`
    - ` 02/01/00`
    - ` 01/02/00`
    - ` 01 Dec 22`
    - ` 22 Dec 01`

   are not, because they are ambigous.

When reading `.serial` files the `tdda` library will accept
any unambiguous date and reject anything it considers ambiguous.
On writing, it will replace any other specific date with
components from 2000-12-31T12:34:56.789+0000.

4. Strings usable by [Python `strftime`](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes)
   can be used.
   These are typified by `%Y-%m-%dT%H:%M:%S`.


On writing new `.serial` files, the library will default to named
`iso8601` formats when the format is conformant with ISO8601,
and will then choose the YYYY/MM/DD type specifier or
`strftime-conforming` strings.

You can specify a preferred form at the command line with
--use-literal-dates, --use-yyyy-dates, --use-pc-dates.


##### ISO 8601 Formats

| Named Format          | `strftime` equivalent         | Example                   |
|:----------------------|:------------------------------|:--------------------------|
| `iso8601-date`        | `%Y-%m-%d`                    | `2000-12-31`              |
| `iso8601-datetime`    | `%Y-%m-%dT%H:%M:%S`           | `2000-12-31T12:34:56`     |
| `iso8601-datetime-tz` | `%Y-%m-%dT%H:%M:%S%z`         | `2000-12-31T12:34:56+00:00` |
| `iso8601`             | Any ISO 8601 date or datetime | Any of the above    |

On read, ISO8601 formats should ideally accept `/` and `.`
as separators for date components in addition to `-` (e.g. `2000/12/31`, `2000.12.31`),
should accept space (`" "`) instead of T,
and should also accept fractional seconds on times.


#### Format Precedence

For each date or datetime field, the format is determined as follows:

1. The field's own `format` key, if present.
2. For `date` fields: the dataset-level `date_format`, if set.
   For `datetime` fields: the dataset-level `datetime_format`, if set.
3. The other dataset-level format (`date_format` falling back to
   `datetime_format` and vice versa).
4. The library default (typically ISO 8601).


### Library-specific Sections

In addition to, or instead of, the `tdda.serial` section, a `.serial`
file can contain sections with library-specific keyword arguments.
These are stored verbatim and used directly when reading or writing
with the corresponding library.

For example, a `pandas.read_csv` section contains exactly the keyword
arguments to be passed to `pandas.read_csv`:

```json
{
    "format": "http://tdda.info/ns/tdda.serial",
    "pandas.read_csv": {
        "sep": "|",
        "encoding": "UTF-8",
        "dtype": {"id": "Int64", "name": "string"},
        "parse_dates": ["joined"],
        "date_format": {"joined": "%d/%m/%Y"},
        "na_values": [""],
        "keep_default_na": false
    }
}
```

When both `tdda.serial` and library-specific sections are present, the
library chooses which to use based on a preference order, or an
explicit preference can be specified.


### Supported Format Abbreviations

When specifying formats to the `tdda serial` command-line tool
(with `--to`), the
following abbreviations are accepted:

| Abbreviation | Full name                      |
|:-------------|:-------------------------------|
| `.`          | `tdda.serial`                  |
| `pd.r`       | `pandas.read_csv`              |
| `pd.w`       | `pandas.DataFrame.to_csv`      |
| `pl.r`       | `polars.read_csv`              |
| `pl.w`       | `polars.DataFrame.write_csv`   |
| `csv.r`      | `python.csv.reader`            |
| `csv.w`      | `python.csv.writer`            |
| `fl`         | `frictionless`                 |
| `fl.r`       | `frictionless.resource`        |
| `fl.p`       | `frictionless.package`         |
| `csvw`       | `csvw`                         |


## Reading Data Using `tdda.serial` Files and other Metadata Specifications

The `tdda` library provides several mechanisms for assisting the reading
of flat files as guided by `tdda.serial`, or by CSVW or Frictionless files,
both as command-line tools and using APIs.

In illustrating the `tdda.serial` functionality, many of the examples
will use this small flat file, which is in a deliberately obscure
format (though all of its features are individually not particularly
uncommon).

%% docdata/docdata.txt
```text
b;i;f;s;t
'n';0;0.5;;31/01/1970
.;.;.;.;.
'Yes';1;1.5;'a';31/12/1999
```

and the following (starting) `tdda.serial` file:

%% docdata/docdata.serial
```
{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-2.2.15",
    "tdda.serial": {
        "fields": [
            {
                "csvname": "b",
                "name": "IAmBoolean",
                "fieldtype": "bool",
                "true_values": [
                    "Yes",
                    "y"
                ],
                "false_values": [
                    "No",
                    "n"
                ]
            },
            {
                "csvname": "i",
                "name": "IAmInt",
                "fieldtype": "int"
            },
            {
                "name": "f",
                "fieldtype": "float"
            },
            {
                "csvname": "s",
                "name": "IAmString",
                "fieldtype": "string"
            },
            {
                "csvname": "t",
                "name": "IAmDate",
                "fieldtype": "datetime",
                "format": "%d/%m/%Y"
            }
        ],
        "encoding": "latin-1",
        "delimiter": ";",
        "quote_char": "'",
        "escape_char": "`",
        "null_indicator": ".",
        "header_row_count": 1,
        "header_row": 0,
        "path": "docdata.txt"
    }
}
```

When read correctly in Pandas, this produces (with the nullable backend
for Pandas to which `tdda.serial` default):

%% docdata/docdata-output.txt
```text
   IAmBoolean  IAmInt     f IAmString    IAmDate
0       False       0   0.5           1970-01-31
1        <NA>    <NA>  <NA>      <NA>        NaT
2        True       1   1.5         a 1999-12-31
dtypes: boolean Int64 Float64 string datetime64[ns]
```

### Reading Flat Files with Metadata from Python using the API

The simplest way to read a flat file with accompanying metadata
is to use the `csv_to_x` functions.  In its simplest forms,


%% docdata/csv2pandas.py
```python
from tdda.serial import csv_to_pandas

df1 = csv_to_pandas('docdata.txt', 'docdata.serial')
df2 = csv_to_pandas('docdata.txt:docdata.serial')
df3 = csv_to_pandas('docdata.txt:')
df4 = csv_to_pandas('docdata.txt', find_md=True)
```

all do the same thing, reading the flat file `docdata.csv` using the metadata
specification in `docdata.serial`. The last two forms are only available when the
`.serial` file has the same stem name as the flat file.

The pandas `dtype` back end can also be passed in, e.g.

%% docdata/csv2pandasbackend.py
```python
from tdda.serial import csv_to_pandas
dfb = csv_to_pandas('docdata.txt', 'docdata.serial', backend='original')
print(dfb)
```

for the original Pandas `dtype` back end.

Similarly
% TODO: polars needs to handle boolean conversion (like dates)

%% docdata/csv2polars.py
```python
from tdda.serial import csv_to_polars

df1 = csv_to_polars('docdata.txt', 'docdata.serial')
df2 = csv_to_polars('docdata.txt:docdata.serial')
df3 = csv_to_polars('docdata.txt:')
df4 = csv_to_polars('docdata.txt', find_md=True)
```

are the equivalent forms for Polars.

**NOTE (`polars.read_csv`):**
Whereas `csv_to_pandas` largely just translates metadata settings
into arguments for `pandas.read_csv`, the corresponding `polars.read_csv`
function is less flexible, and there are number of kidns of flat files
that it struggles to read accurately. A particular example of this is
that polars can only read ISO8601-formatted dates and datestamps.
The `tdda.serial` `csv_to_polars` works around this by instructing
polars to read fields it cannot parse with `read_csv` as strings
and then post-processing them to convert them to date or datetime fields.

### Metadata Matching and `@` wildcards

When a colon is added to the end of a flat file name or path
to request that `tdda.serial` finds matching metadata,
and then `find_metadata=True` is passed into relevant API calls,
`tdda`'s matching process for a file `foo.ext` is as follows:

1. It first looks for `foo.ext.serial` (in the same directory as `foo.ext`).

2. It first looks for `foo.serial` (in the same directory as `foo.ext`).
   (This the most common pattern; `foo.ext.serial` is checked first to
   allow matching of metadata when the same stem appears with multiple
   extensions, e.g. `.csv` and `.psv`)

3. Failing that, it looks for any wildcard matches using `@` as a wildcard
   similar to how `*` is used in globbing, i.e. `@` matches any characters
   or no characters. So for example any of

    - `@.serial`
    - `foo@.serial`
    - `@foo.serial`
    - `@f@o@.serial`

   will match, but none of

    - `Foo.serial`
    - `fool*.serial`
    - `f0*.serial`

   will do so. If a single metadata file containing `@` matches,
   that will be used. If multiple `.serial` files with wildcards
   match, an error will be raised.

4. Next, the following are checked:

    - `foo-metadata.json`
    - `foo-csvmetadata.json`
    - `foo-csv-metadata.json`
    - `foo.csvmetadata`
    - `foo.csv-metadata`

   These are common patterns for CSVW, and will be used as CSVW
   if the `@context` attribute indicates csvw, and as `tdda.serial`
   if the `format` attribute indicates that.

5. Common Frictionless patterns are explored. Frictionless usually
   used either `.yaml` or `.json`, and includes either `.resource`,
   `.package`, or `.schema` in the filename before it, so any of:

    - `foo.resource.json`
    - `foo.package.json`
    - `foo.schema.json`
    - `foo.resource.yaml`
    - `foo.package.yaml`
    - `foo.schema.yaml`

   will match.


### Pandas `dtype` Back Ends

Pandas has three different back ends for storing data.
Its `original` one uses floating-point columns whenever integer fields
contain null (`na`) values, and use the object type for strings,
as well as for various other things.

More recent versions of Pandas have introduced support for
nullable integers (e.g. `Int64`) and a proper `string` type.
This backend is called `nullable_numpy`.

Even more recently, Pandas has also added an (Apache) `pyarrow` backend,
which also has (different) nullable integers and `string` types.

A single DataFrame can contain columns with any mixture of these types.

The `tdda.serial` library supports all of these backends, but defaults
to the `nullable_numpy` backend. In general, alternate backends may be
specified with either the command-line switch `--backend` or `-B`,
with values:

 - `o` or `original` for the original back end,
 - `n` or `numpy_nullable` for the `numpy_nullable` back end, and
 - `a` or `pyarrow` for the `pyarrow` back end.

The API generally used a `backend` keyword argument on calls to specify
the backend when appropriate.






CSVW and Frictionless data may also be used in place of .serial files.
In the case of CSVW, the most common file name format is:

 * `docdata-metadata.json`

for data `docdata.csv`, and one of

 * `docdata.resource.yaml`
 * `docdata.resource.json`
 * `docdata.package.yaml`
 * `docdata.package.json`

for Frictionless.

If the metadata specifies the name of the flat file (which is usual
for csvw and Frictionless, and allowed for tdda.serial) then the
metadata file itself can be specified instead. For example:

%% docdata/pandas-and-polars-reads.py
```python
from tdda.serial import csv_to_polars, csv_to_pandas

df1 = csv_to_pandas('docdata.serial')
df2 = csv_to_polars('docdata-metadata.json')
df3 = csv_to_polars('docdata.resource.yaml')
```

would use three different metadata files that point to data
to read them into three dataframes, the first using Pandas
and the last two using Polars.

**NOTE: (full function arguments)**
There are more optional parameters to the `csv_to_pandas`
and `csv_to_polars` functions;
see the detailed API documentation for details.


### Using the `tdda serial` Command to Assist with Reading Flat Files

The `tdda serial` command can generate Python code or sets of keyword
arguments for `read_csv` methods from Pandas or Polars.

%% docdata/tddaserial1.sh
```bash
tdda serial docdata.serial docdata_pandas.py --to pd.r
```

This command generates stand-alone Python code `docdata.py` containing
a function for reading flat file in the format specified by `docdata.serial`
with Pandas, taking the path to the datafile as an argument.
(Standalone, here, means code that does not require the `tdda` library.)

%% docdata/tddaserial2.sh
```bash
tdda serial docdata.serial docdata_polars.py --to pl.r
```

This command generates Python code `docdata.py` containing a function
for reading flat file in the format specified by docdata.serial
with Polars, taking the path to the datafile as an argument.

The `--for` parameter can be added so that the generated Python
calls the function with the appropriate inpath. For example:

% TODO: This doesn't seem to work currently

%% docdata/tddaserial3.sh
```bash
tdda serial docdata.serial docdata_polars2.py --to pl.r --for docdata.txt

```

## Writing Data with `tdda.serial` (API)

Just as `csv_to_pandas` and `csv_to_polars` read flat files
into dataframes for the two libraries, `pandas_to_csv` and
`polars_to_csv` *write* data.
Metadata files can have two roles in this process:

 * Metadata files can be written *with* the flat data to specify
   the format used (these can be `.serial` files, or CSVW files,
   or Frictionless files).
 * Metadata files can be used to *specify* the write format.

These two roles can be combined.

### The `pandas_to_csv` function

The simplest form for writing a Pandas dataframe to CSV *with
metadata* is:

%% docdata/pandas2csv1.py
```python
from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata1pd.csv', md_outpath='docdata1pd.serial')
```

This will write a the Pandas dataframe `df` to `docdata2.csv` using
`df.to_csv`, with default settings,
and writing accompanying metadata to `docdata2pd.serial`.

Specific write formatting parameters can be passed directly to
`to_csv` as keyword arguments, and these will also, where appropriate,
affect the written metadata in the `.serial` file. For example:

%% docdata/pandas2csv2.py
```python
from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata2pd.csv', md_outpath='docdata2pd.serial',
              sep='|', na_rep='NULL', quotechar="'")
```

will write the data using a pipe separator (`|`), single quotes (`'`),
and `NULL` as the null marker, and the resulting `.serial` file
will document those settings.

Instead of providing settings as keyword parameters, a metadata file
can be used to determine the flat-file write settings using the
`md_inpath` argument. So if we want to write the data in a DataFrame
using the metadata in `docdata.serial`, we can use:

%% docdata/pandas2csv3.py
```python
from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata3pd.csv', md_inpath='docdata.serial')
```

This does *not* write a serial file.

It is occasionally useful to specify both an `in_metadata`
and an `out_metadata` path, like this:

%% docdata/pandas2csv4.py
```python
from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata4pd.csv', md_inpath='docdata.serial',
              md_outpath='docdata4pd.serial')

```

The reasons for wanting to write metadata when a metadata file is
used to specify the write format might include:

 - The input and output metadata formats might be different
   (e.g. `tdda.serial` in and CSVW out)
 - A central metadata file in one location might be used to specify
   the format, and the output format file might be in a different
   location, e.g. by the data file written
 - The output metadata can include a pointer to the specific dataset.
   This is normal in the case of CSVW and Frictionless,
   and optional in the case of `tdda.serial`.

### The `polars_to_csv` function

The polars function works in the same was as its Pandas counterpart.

The simplest form for writing a polars dataframe to CSV *with
metadata* is:

%% docdata/polars2csv1.py
```python
from tdda.serial import polars_to_csv, csv_to_polars

df = csv_to_polars('docdata.txt:')
polars_to_csv(df, 'docdata1pl.csv', md_outpath='docdata1pl.serial')
```

This will write a the Polars dataframe `df` to `docdata2.csv` using
`df.to_csv`, with default settings,
and writing accompanying metadata to `docdata2pd.serial`.

Specific write formatting parameters can be passed directly to
`to_csv` as keyword arguments, and these will also, where appropriate,
affect the written metadata in the `.serial` file. For example:

%% docdata/polars2csv2.py
```python
from tdda.serial import polars_to_csv, csv_to_polars

df = csv_to_polars('docdata.txt:')
polars_to_csv(df, 'docdata2pl.csv', md_outpath='docdata2pl.serial',
              sep='|', na_rep='NULL', quotechar="'")
```

will write the data using a pipe separator (`|`), single quotes (`'`),
and `NULL` as the null marker, and the resulting `.serial` file
will document those settings.

Instead of providing settings as keyword parameters, a metadata file
can be used to determine the flat-file write settings using the
`md_inpath` argument. So if we want to write the data in a DataFrame
using the metadata in `docdata.serial`, we can use:

%% docdata/polars2csv3.py
```python
from tdda.serial import polars_to_csv, csv_to_polars

df = csv_to_polars('docdata.txt:')
polars_to_csv(df, 'docdata3pl.csv', md_inpath='docdata.serial')
```

This does *not* write a serial file.

It is occasionally useful to specify both an `in_metadata`
and an `out_metadata` path, like this:

%% docdata/polars2csv4.py
```python
from tdda.serial import polars_to_csv, csv_to_polars

df = csv_to_polars('docdata.txt:')
polars_to_csv(df, 'docdata4pl.csv', md_inpath='docdata.serial',
              md_outpath='docdata4pl.serial')

```

The reasons for wanting to write metadata when a metadata file is
used to specify the write format might include:

 - The input and output metadata formats might be different
   (e.g. `tdda.serial` in and CSVW out)
 - A central metadata file in one location might be used to specify
   the format, and the output format file might be in a different
   location, e.g. by the data file written
 - The output metadata can include a pointer to the specific dataset.
   This is normal in the case of CSVW and Frictionless,
   and optional in the case of `tdda.serial`.
% TODO: for tdda.serial


**NOTE:** There are more optional parameters to the `polars_to_csv`
and `csv_to_polars` functions;
see the detailed API documentation for details.


## Generating `tdda.serial` Files by Inference from a Flat File

**Experimental Functionality**

The `tdda.serial` library can also read a flat file and attempt
to infer its format and write it to a `tdda.serial` or other
metadata file using the `--generate` (or `-g`) switch.
This is an inherently heuristic process and results cannot be guaranteed
to be correct.

The general approach used in `tdda`'s format inference is only to write
that for which there is evidence in the data, i.e. it does not write
default values to the `tdda.serial` or other metadata files. So for example,
if there are no quote characters used in a datafile, the quote character
will not be set. Similarly, if the data is pure ASCII, no encoding will
be written to the file.

Basic usage is as follows:

%% docdata/inference1.sh
```bash
tdda serial --generate docdata.txt docdata-inferred.serial
```

Warnings will be issued in some cases if the inference process has
sinificant ambiguity, and the process may fail if `tdda.serial` cannot
infer the format.

Overrides for most top-level parameters can be provided with switches.
These can be used as hints, e.g. specifying an encoding where in cases
where this cannot be inferred, or to select alternatives if, for example,
the inference process infers `iso-8859-1` (`latin-1`) but the data is in fact
`iso-8859015` (`latin-9`) or `cp1252`. (These encodings are hard to
differentiate.)

The overrides will normally be accepted except in cases where it is
too obviously in conflict with the data, which complicates further inference.

The available Override switches are:

`--sep C`, `--delimiter C`
: Set field delimiter to `C`

`--quote-char Q`, `--quote Q`
: Set the quote character to `Q` (normally strigaht single or double quote)

`--escape`
: Set the escape character to backslash (no argument)

`--no-escape`
: Do not set the escape character

`--stutter`
: Specify stuttering for embedded quotes

`--no-stutter`
: Specify that quotes are not stuttered (usually implying escaping)

`--date-format FMT`
: Use `FMT` as the default date format for the file (can be a named
  format or a `%`-string suitable for Python's `strftime`.

`--datetime-format FMT`
: Use `FMT` as the default datetime format for the file (can be a named
  format or a %-string suitable for Python's `strftime`.

% TODO:
`--quoting STYLE`
: Specifies that the quoting style should be set to `STYLE`,
  which must be one of Python `csv`'s `QUOTE` styles or
  the `tdda`-specific JSON-style `QUOTE_STRINGS_ONLY`.


In addition to these overrides, other useful switches for inference are:

`--sample-lines N`, `-n N`
: Specify the number of lines to use for inference.
  This defaults to 1000. (This will be reduced to the number of lines
  in the file if it is larger than that.)

`--single`, `-1`
: Specifies that there is only one field in the file.
  Single-field files cause difficulty with finding the field delimiter.

`--Verbose`, `-V`
: Be highly verbose.

`--verbose`, `-v`
: Be somewhat verbose.

`--quiet`, `-q`
: Be as quiet as practical.


### Creating Fieldless `tdda.serial` files

It is sometimes desirable to create a `tdda.serial` file that contains
specification of whole-file-level properties only, e.g., delimiter,
quote character etc.---in fact, the very things that support overrides
with command-line switches. If the filename is set to empty, such
a metadata file can be generated. For example:

%% docdata/generation1.sh
```bash
tdda serial --generate '' generated.serial --null NULL --sep '|' --quote-char "'"

```

will generate a `tdda.serial` file with only those properties specified:

%% docdata/generated.serial
```
{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-3.0.00rc1",
    "tdda.serial": {
        "delimiter": "|",
        "quote_char": "'",
        "null_indicator": "NULL"
    }
}
```

This can either be used directly, allowing the chosen flat-file reader
to figure out field names, types and per-field formats, or can be used
as the starting point for a more detailed `.serial` file including
hand-crafted field specifications.



## Converting Between `tdda.serial`, CSVW, and Frictionless

**Experimental Functionality**

The `tdda.serial` module has some ability to convert between different
`tdda.serial` formats and between `tdda.serial`, CSVW, and Frictionless
metadata specifications. There are limitations in all cases, but
the most important specifications generally work.

Here are some example conversion commands:

%% docdata/convert1.sh
```bash
tdda serial docdata.serial docdata-metadata.json
tdda serial docdata.serial docdata-metadata-from-serial2.json --to csvw

```

The first command produces `docdata-metadata.json` as CSVW, assuming
a CSVW target because the pattern fits the normal CSVW convention.

The second version uses a non-standard name for the CSVW metadata,
so the `--to` flag needs to be used to specify `csvw` as the target
format.

The result is:

%% docdata/docdata-metadata-from-serial2.json
```json
{
    "@context": "http://www.w3.org/ns/csvw",
    "dc:conformsTo": "data-package",
    "dc:creator": "tdda.serial-3.0.00rc1",
    "tables": [
        {
            "tableSchema": {
                "columns": [
                    {
                        "name": "b",
                        "datatype": {
                            "base": "boolean",
                            "format": "Yes|No"
                        }
                    },
                    {
                        "name": "i",
                        "datatype": "integer"
                    },
                    {
                        "name": "f",
                        "datatype": "float"
                    },
                    {
                        "name": "s",
                        "datatype": "string"
                    },
                    {
                        "name": "t",
                        "datatype": {
                            "base": "datetime",
                            "format": "dd/MM/yyyy"
                        }
                    }
                ]
            },
            "url": "docdata.txt"
        }
    ],
    "dialect": {
        "encoding": "latin-1",
        "delimiter": ";",
        "headerRowCount": 1,
        "quoteChar": "'"
    },
    "null": "."
}
```

% Why is a warning issued? Doesn't CSVW understand that format?

---

%% docdata/convert2.sh
```bash
tdda serial docdata.serial docdata.package.yaml
tdda serial docdata.serial docdata.resource.json


```

These two commands produce Frictionless metadata specifications.
The first produces a Frictionless package metadata files as YAML,
while the second produces a Frictionless resource metadata description
as JSON. Again, the names are conventional for Frictionless, so the
format is inferred. Again `--to frictionless` or `--to fless` could
be used to specify this if an unconventional name were used.

% .ssv again!

The YAML package output is:

%% docdata/docdata.package.yaml
```yaml
resources:
- name: docdata
  type: table
  path: docdata.txt
  scheme: file
  format: csv
  mediatype: text/csv
  encoding: latin-1
  dialect:
    header: true
    headerRows:
    - 0
    delimiter: ;
    quoteChar: ''''
    escapeChar: '`'
  schema:
    fields:
    - name: b
      type: boolean
      trueValues:
      - 'Yes'
      - y
      falseValues:
      - 'No'
      - n
    - name: i
      type: integer
    - name: f
      type: number
    - name: s
      type: string
    - name: t
      type: datetime
    missingValues:
    - .
```

and the JSON resource output is

%% docdata/docdata.resource.json
```json
{
    "name": "docdata",
    "type": "table",
    "path": "docdata.txt",
    "scheme": "file",
    "format": "csv",
    "mediatype": "text/csv",
    "encoding": "latin-1",
    "dialect": {
        "header": true,
        "headerRows": [
            0
        ],
        "delimiter": ";",
        "quoteChar": "'",
        "escapeChar": "`"
    },
    "schema": {
        "fields": [
            {
                "name": "b",
                "type": "boolean",
                "trueValues": [
                    "Yes",
                    "y"
                ],
                "falseValues": [
                    "No",
                    "n"
                ]
            },
            {
                "name": "i",
                "type": "integer"
            },
            {
                "name": "f",
                "type": "number"
            },
            {
                "name": "s",
                "type": "string"
            },
            {
                "name": "t",
                "type": "datetime"
            }
        ],
        "missingValues": [
            "."
        ]
    }
}
```

---

In the case of converting to a Pandas `csv_read` specification, a
`dtype` back end can be specified. So we might say:

%% docdata/convert3.sh
```bash
tdda serial docdata.serial docdata-pd.r-o.serial --to pd.r -B o



```

will ask for the `pandas.read_csv` version of a `tdda.serial` file
using the original Pandas `dtype` backend.

The result is:

%% docdata/docdata-pd.r-o.serial
```
{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-3.0.00rc1",
    "pandas.read_csv": {
        "sep": ";",
        "encoding": "latin-1",
        "escapechar": "`",
        "quotechar": "'",
        "dtype": {
            "IAmBoolean": "object",
            "f": "float",
            "IAmString": "object"
        },
        "date_format": {
            "IAmDate": "%d/%m/%Y"
        },
        "parse_dates": [
            "IAmDate"
        ],
        "na_values": ".",
        "keep_default_na": false,
        "names": [
            "IAmBoolean",
            "IAmInt",
            "f",
            "IAmString",
            "IAmDate"
        ],
        "header": 0,
        "true_values": [
            "Yes",
            "y"
        ],
        "false_values": [
            "No",
            "n"
        ]
    }
}
```

---

The source does not have to be a `tdda.serial` file: `tdda.serial` can convert
between any supported formats and (in the case of Pandas, any of the
`dtype` back ends).


## Custom Sections within `tdda.serial` Files

The primary goals of the `tdda.serial` format are to allow detailed
specification of flat-file formats and to provide facilites for
utilising such specifications for more accurate reading and writing
of data using (inherently ambiguous) flat-file formats. The `tdda.serial`
specifications are not written with a single library in mind, and are
intended, where possible, to be sufficiently general to allow
use with various libraries.

If, however, a single library is to be used, there is still potentially
value in recording read and write settings for that library in an
companion metadata file, and `tdda.serial` can serve that function too.
Where library parameters are expressible as JSON (i.e. nulls, numbers,
strings, booleans, arrays, and dictionaries), they can simply be written
into a relevant section of a `tdda.serial` file.

For example, we can convert the [Example](#Example) `tdda.serial` file
to ond that contains custom sections for Pandas `read_csv` function
and `DataFrame.to_csv` methods as follows:

%% docdata/converttopd.sh
```bash
tdda serial example.serial examplepd.serial --to pd.r,pd.w
```

(Here we have specified both `pd.r` and `pd.w`, but we could have requested
only one of them.)

The result is the following file:

%% docdata/examplepd.serial
```
{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-3.0.00rc1",
    "pandas.read_csv": {
        "sep": "|",
        "encoding": "UTF-8",
        "escapechar": "\\",
        "quotechar": "\"",
        "doublequote": false,
        "dtype": {
            "id": "Int64",
            "name": "string"
        },
        "date_format": {
            "joined": "ISO8601",
            "last_seen": "%m/%d/%Y %H:%M:%S"
        },
        "parse_dates": [
            "joined",
            "last_seen"
        ],
        "na_values": "",
        "keep_default_na": false
    },
    "pandas.DataFrame.to_csv": {
        "sep": "|",
        "encoding": "UTF-8",
        "escapechar": "\\",
        "quotechar": "\"",
        "doublequote": false,
        "date_format": "%Y-%m-%d",
        "na_rep": ""
    }
}
```

The reason `tdda.serial` supports both read and write sections for
libraries such as Pandas and Polars is that the parameters for reading
and writing are different in various ways. First, most libraries aim to
write consistently (e.g. using a single null marker and a consistent
date format), so allow fewer things to be specified on write. They also
use different parameter names in some cases.


Things are slightly more complicated when the parameters are not naturally
espressible in JSON, as is the case with Polars types, which are passed
as `type` objects. In this case, `tdda.serial` converts such objects
to strings and the `csv_to_polars` method handles this when it uses them.

So, considering only the read case, the Polars equivalent conversion is:
% TODO: pl.w

%% docdata/converttopl.sh
```bash
tdda serial example.serial examplepl.serial --to pl.r
```

which produces:

%% docdata/examplepl.serial
```
{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-3.0.00rc1",
    "polars.read_csv": {
        "separator": "|",
        "quote_char": "\"",
        "null_values": [
            ""
        ],
        "encoding": "UTF-8",
        "schema": {
            "id": "Int64",
            "name": "String",
            "joined": "Datetime",
            "last_seen": "String"
        }
    }
}
```

Here, `last_seen` set to type `String` (i.e. `polars.String`) because
Polars will no understand the date format. However, if the Python read
code is generated with

%% docdata/converttopl.sh
```bash
tdda serial example.serial examplepl.serial --to pl.r
```

all is handled:

%% docdata/examplereadpl.py
```python
import polars as pl

def read_data(inpath):
    df = pl.read_csv(
        inpath,
        separator='|',
        quote_char='"',
        null_values=[''],
        encoding='UTF-8',
        schema={
            'id': pl.Int64,
            'name': pl.String,
            'joined': pl.Datetime,
            'last_seen': pl.String
        }
    )

    df = df.with_columns([
        pl.col('last_seen').str.to_datetime(format='%m/%d/%Y %H:%M:%S'),
    ])
    return df

```

