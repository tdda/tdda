# The `tdda.serial` File Format

A `.serial` file is a JSON file describing the format of one or more
flat files (CSV files and similar). It is the primary metadata format
used by the `tdda.serial` library.

A single `.serial` file can describe a format shared by many concrete
flat files, unlike CSVW, which is primarily concerned with describing
specific named files. A `.serial` file can also contain
library-specific sections (for `pandas.read_csv`, `polars.read_csv`
etc.) alongside or instead of the `tdda.serial` section.

## File Structure

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

### Top-level Keys

**`format`** *(string, required)*
: Must be `"http://tdda.info/ns/tdda.serial"`. Identifies the file as
  a `tdda.serial` file.

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
be specified explicitly.

---

## The `tdda.serial` Section

This section contains a dataset-level description of the flat file
format, with optional per-field overrides.

### Example

```json
{
    "format": "http://tdda.info/ns/tdda.serial",
    "tdda.serial": {
        "encoding": "UTF-8",
        "delimiter": "|",
        "quote_char": "\"",
        "escape_char": "\\",
        "stutter_quotes": false,
        "null_indicator": "",
        "date_format": "iso8601-date",
        "datetime_format": "eu-datetime",
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
                "format": "us-datetime"
            }
        ]
    }
}
```

### Dataset-level Keys

All dataset-level keys are optional.

**`encoding`** *(string)*
: The text encoding of the file. Any Python codec name is accepted,
  e.g. `"UTF-8"`, `"latin-1"`. Default: `"UTF-8"`.

**`delimiter`** *(string)*
: The field separator character. Default: `","`.

**`quote_char`** *(string)*
: The character used to quote fields containing the delimiter or
  newlines. Default: `"\""`.

**`escape_char`** *(string)*
: The character used to escape the quote character within a quoted
  field (when not using stutter quoting). Default: `"\\"`.

**`stutter_quotes`** *(boolean)*
: If `true`, the quote character is escaped by doubling it (Excel
  style). If `false`, the escape character is used. Default: `false`.

**`null_indicator`** *(string or array of strings)*
: The string or strings used to represent null/missing values.
  Default: `""` (empty string).

**`date_format`** *(string)*
: The default format for `date` fields that have no per-field
  `format`. Also used as the fallback for `datetime` fields if
  `datetime_format` is not set. Accepts named formats (see
  [Date and Datetime Formats](#date-and-datetime-formats)) or Python
  strftime strings. Default: `"iso8601-date"`.

**`datetime_format`** *(string)*
: The default format for `datetime` fields that have no per-field
  `format`. If not set, `date_format` is used as the fallback.
  Accepts named formats or Python strftime strings.

**`header_row_count`** *(integer)*
: The number of header rows at the top of the file. Default: `1`.

**`header_row`** *(integer)*
: The zero-based index of the row containing column names, within the
  header rows. Default: `0`.

**`accept_percentages_as_floats`** *(boolean)*
: If `true`, values like `"12.5%"` are read as `0.125`. Default:
  `false`.

**`map_missing_trailing_cols_to_null`** *(boolean)*
: If `true`, rows with fewer fields than expected (as Excel sometimes
  produces) have missing trailing fields treated as null. Default:
  `false`.

**`decimal_point`** *(string)*
: The character used as the decimal point in numeric fields. Default:
  `"."`.

**`thou_sep`** *(string)*
: The thousands separator character in numeric fields, e.g. `","`.
  Optional; no default.

**`true_values`** *(string or array of strings)*
: String values to interpret as `True` for boolean fields, in addition
  to the library defaults. Applies to all `bool` fields unless
  overridden per field.

**`false_values`** *(string or array of strings)*
: String values to interpret as `False` for boolean fields, in addition
  to the library defaults. Applies to all `bool` fields unless
  overridden per field.

**`fields`** *(array or object)*
: Descriptions of the fields in the file. See
  [The `fields` Entry](#the-fields-entry).

---

### The `fields` Entry

Fields can be specified as either an **array** or an **object
(dictionary)**.

**Array form** — the field list is taken to be complete and ordered.
Fields appear in the order they occur in the file. Each entry is a
field object (described below).

```json
"fields": [
    { "name": "id", "fieldtype": "int" },
    { "name": "date", "fieldtype": "date" }
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
    "commission date": { "name": "DateOfCommission", "fieldtype": "date" },
    "qa passed?":      { "name": "PassedQA", "fieldtype": "bool",
                         "true_values": "yes", "false_values": "no" }
}
```

### Field Keys

**`name`** *(string, required in array form)*
: The internal name for the field — the column name used in the
  resulting dataframe. In array form this is mandatory. In object form
  it can be omitted if the internal name is the same as the external
  (dictionary key) name.

**`fieldtype`** *(string)*
: The type of the field, from the table below.

| Value          | Description                              |
|----------------|------------------------------------------|
| `bool`         | Boolean                                  |
| `int`          | Integer                                  |
| `float`        | Floating-point                           |
| `number`       | Integer or float (inferred)              |
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
  Accepts named formats or Python strftime strings (see
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

---

## Date and Datetime Formats

Date and datetime formats can be specified as either a **named format**
or a **Python strftime string**.

### Named Formats

Named formats are portable identifiers for common date and datetime
conventions. They are preferred over raw strftime strings because they
are clearer, more portable, and allow the `tdda.serial` library to make
appropriate choices for different libraries (e.g. passing `"ISO8601"`
to Pandas rather than a specific strftime string for ISO 8601 dates).

#### ISO 8601 Formats

| Named Format        | Description                          | Example                   |
|---------------------|--------------------------------------|---------------------------|
| `iso8601-date`      | ISO 8601 date                        | `2024-01-15`              |
| `iso8601-datetime`  | ISO 8601 datetime                    | `2024-01-15T12:34:56`     |
| `iso8601-datetime-tz` | ISO 8601 datetime with timezone    | `2024-01-15T12:34:56+01:00` |
| `iso8601`           | ISO 8601 date or datetime (unspecified) | either of the above    |

#### European Formats

Day before month (`DD/MM/YYYY`).

| Named Format        | strftime equivalent      | Example                   |
|---------------------|--------------------------|---------------------------|
| `eu-date`           | `%d/%m/%Y`               | `15/01/2024`              |
| `eu-date-2y`        | `%d/%m/%y`               | `15/01/24`                |
| `eu-datetime`       | `%d/%m/%Y %H:%M:%S`      | `15/01/2024 12:34:56`     |
| `eu-datetime-2y`    | `%d/%m/%y %H:%M:%S`      | `15/01/24 12:34:56`       |

On read, European formats also accept `-` and `.` as separators in
addition to `/` (e.g. `15-01-2024`, `15.01.2024`).

#### US Formats

Month before day (`MM/DD/YYYY`).

| Named Format        | strftime equivalent      | Example                   |
|---------------------|--------------------------|---------------------------|
| `us-date`           | `%m/%d/%Y`               | `01/15/2024`              |
| `us-date-2y`        | `%m/%d/%y`               | `01/15/24`                |
| `us-datetime`       | `%m/%d/%Y %H:%M:%S`      | `01/15/2024 12:34:56`     |
| `us-datetime-2y`    | `%m/%d/%y %H:%M:%S`      | `01/15/24 12:34:56`       |

On read, US formats also accept `-` as a separator.

### strftime Strings

Any Python strftime format string is also accepted, e.g. `"%d/%m/%Y"`
or `"%Y-%m-%d %H:%M:%S"`. Named formats are preferred where one
exists, as they are more portable across libraries.

### Format Precedence

For each date or datetime field, the format is determined as follows:

1. The field's own `format` key, if present.
2. For `date` fields: the dataset-level `date_format`, if set.
   For `datetime` fields: the dataset-level `datetime_format`, if set.
3. The other dataset-level format (`date_format` falling back to
   `datetime_format` and vice versa).
4. The library default (typically ISO 8601).

---

## Library-specific Sections

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

---

## Supported Format Abbreviations

When specifying formats to the `tdda serial` command-line tool, the
following abbreviations are accepted:

| Abbreviation | Full name                      |
|--------------|--------------------------------|
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
