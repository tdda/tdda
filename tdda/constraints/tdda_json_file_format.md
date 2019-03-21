# The `.tdda` JSON File Format

The tdda constraints library (Repository
[http://github.com/tdda/tdda](http://github.com/tdda/tdda),
module `constraints`)
uses a JSON file to store constraints.

This document seeks to specify that file format.

# Purpose

TDDA files describe *constraints* on a *dataset* with a view to
*verifying* the dataset to check whether any or all of the specified
constraints are satisfied.

A dataset is assumed to consist of one or more *fields* (also known
as columns), each of which has a (different) name and a type.
Each field has a *value* for each of zero or more *records* (also
known as rows). In some cases, values may be `null` (or missing).
Even a field consting entirely of nulls can be considered to have
a type.

Familiar examples of datasets include:

  * tables in relational databases
  * DataFrames in (Pandas and R)
  * Flat ("CSV") files (subject to type inference or assigment)
  * Sheets in spreadsheets, or areas within spreadsheet sheets,
    if the columns have names, are not merged, and have values
    with consistent meanings down an entire column.
  * More generally, many forms of tabular data.

In principle, TDDA files are intended to contain any kind of constraint
regarding datasets. Today, we are mostly concerned with field types,
minimum and maximum values, whether nulls are allowed, whether repeated
values are allowed within a field, and the allowed values for a field.
We may also be concerned with relations between fields.

Likely extensions might include

  * dataset-level constraints (e.g. numbers of records; required or barred
    fields)
  * sortedness
  * constraints on subsets of the data
  * constraints substructure within fields (e.g. satisfying regular
    expressions, or constraints on sub-portions of fields).
  * potentially checksums (though this is more suitable for checking
    the integreity of transfer of a specific dataset, than for use
    across multiple related datasets).

The motivation for generating, storing and verifying datasets against
such sets of constraints is that they can provide a powerful way of
detecting bad or unexpected inputs to or outputs from a data analysis
process. They can also be valuable as checks on intermediate results.

## Filename and encoding

The preferred extension for TDDA Constraints files is `.tdda`.

`.tdda` files must be encoded as UTF-8.

The file should (must) be valid JSON.

## Example

This is an extremely simple example TDDA file:

    {
        "fields": {
            "a": {
                "type": "int",
                "min": 1,
                "max": 9,
                "sign": "positive",
                "max_nulls": 0,
                "no_duplicates": true
            },
            "b": {
                "type": "string",
                "min_length": 3,
                "max_length": 3,
                "max_nulls": 1,
                "no_duplicates": true,
                "allowed_values": [
                    "one",
                    "two"
                ]
            }
        }
    }

## General Structure

A `.tdda` file is a dictionary with two currently-supported top-level keys:

 * `fields`: constraints for individual fields, keyed on the field name.
   (In TDDA, we generally refer to dataset `columns` as fields.)

 * `field_groups`: constraints specifying relations between two or more
   fields (usually two, for now). `field_group` constraints are keyed
   on a comma-separated list of the names of the fields to which they
   relate, and order is significant.

Both top-level keys are optional (though if you have neither, there's not
a whole lot of constraining going on!)

In future, we certainly expect to add further top-level keys (e.g. for
possible constraints on the number of rows, required or banned fields etc.)

The order of fields in the file is immaterial (of course; this is JSON),
though writers may choose to present fields in a particular order,
e.g. dataset order or sorted on fieldname.


# Field Constraints

The value of a field constraints entry is a dictionary keyed on constraint
*kind*. For example, the constraints on field `a` in the example above are
specified as:

    "a": {
        "type": "int",
        "min": 1,
        "max": 9,
        "sign": "positive",
        "max_nulls": 0,
        "no_duplicates": true
    }

The TDDA library recognized the following *kind*s of constraints:

  * `type`
  * `min`
  * `max`
  * `min_length`
  * `max_length`
  * `sign`
  * `sign`
  * `max_nulls`
  * `no_duplicates`
  * `allowed_values`
  * `rex`

Other constraint libraries are free to define their own, custom kinds of
constraints.

The value of a constraint is often simply a scalar value, but can be a list
or a dictionary; when it is a dictionary, it should include `value`.

If the value of a constraint (the scalar value, or the `value` key if the
value is a dictionary) is `null` (Python: `None`), this is taken to indicate
the absense of a constraint. A constraint with value `None` should be
completely ignored, so that a constraints file including `null`-valued
constraints should produce identical results to one omitting those constraints.

The semantics and values of the standard field constraint types are as follows:

  * `type`: the allowed (standard, TDDA) type of the field.
    This can be a single value from `bool` (boolean),
    `int` (integer; whole-numbered); `real` (floating point values);
    `string` (unicode in Python3; byte string in Python2) or 'date'
    (any kind of date or date time, with or without timezone information).
    It can also be a list of such allowed values (in which case, order
    is not significant.

    It is up to the generation and verification libraries to map between
    the actual types in whatever dataset/dataframe/table/... object is
    used.

    Examples:

      * `{"type": "int"}`
      * `{"type": ["int", "real"]}`

  * `min`: the minimum allowed value for a field. This is often
    a simple value, but in the case of real fields, it can be
    convenient to specify a level of precision. In particular,
    a minimum value can be

      * `closed`: all non-null values in the field must be
        greater than or equal to the value specified.
      * `open`: all non-null values in the field must be
        strictly greater than the value specified.
      * `fuzzy`: when the precision is specified as *fuzzy*,
        the verifier should allow a small degree of violation
        of the constraint without generating a failure.
        (This is the default.) Verifiers take a parameter,
        `epsilon`, which specifies how the fuzzy constraints
        should be taken to be: epsilon is a fraction of the
        constraint value by which field values are allowed
        to exceed the constraint without being considered
        to fail the constraint. This detaults to 0.01 (i.e. 1%).
        Notice that this means that constraint values of zero
        are never fuzzy.

   Examples are:

     * `{"min": 1}`,
     * `{"min": 1.2}`,
     * `{"min": {"value": 3.4}, {"precision": "fuzzy"}}`.

  * `max`: the maximum allowed value for a field. Much like `min`,
    but for maximum values.
    Examples are:

      * `{"max": 1}`,
      * `{"max": 1.2}`,
      * `{"max": {"value": 3.4}, {"precision": "closed"}}`.

  * `min_length`: the minimum allowed length of strings in a string field.
    How unicode strings are counted is up to the implementation.
    Example:

      * `{"min_length": 2}`


  * `max_length`: the minimum allowed length of strings in a string field.
    How unicode strings are counted is up to the implementation.

      * `{"max_length": 22}`

  * `sign`: For numeric fields, the allowed sign of (non-null)
    values.  Although this overlaps with minimum and maximum
    values, it it often useful to have a separate sign constraint,
    which carries semantically different information. Allowed
    values are:

       - `positive`: All values must be greater than zero
       - `non-negative`: No value may be less than zero
       - `zero`: All values must be zero
       - `non-positive`: No value may be greater than zero
       - `negative`: All values must be negative
       - `null`: No signed values are allowed, i.e. the field must
         be entirely null.

    Example:

      * `{"sign": "non-negative"}`

  * `max_nulls`: The maximum number of nulls allowed in the field.
    This can be any non-negative value. We recommend only writing
    values of zero (no nulls values are allowed) or 1 (At most a
    single null is allowed) into this constraint, but checking
    against any value found.

    Example:

      * `{"max_nulls": 0}`

  * `no_duplicates`: When this constraint is set on a field (normally
    with value True), it means that each non-null value must occur
    only once in the field. The current implementation only uses
    this constraint for string fields.

    Example:

      * `{"no_duplicates": true}`

  * `allowed_values`: The value of this constraint is a list of
    allowed values for the field. The order is not significant.

    Example:

      * `{"allowed_values": ["red", "green", "blue"]}`

  * `rex`: The value of this constraint is a list of
    regular expressions for matching the values from the field.
    The order is not significant. The constraint passes if
    at least one of the regular expressions matches, for each
    value in the field.

    Example:

      * `{"ref": ["^[A-Z][a-z]+$", "^[0-9]+$", "^$", "^#"]}`


# MultiField Constraints

These are constraints between pairs of fields, such as for specifying that
one date field must always be earlier than another date field (for specifying
`start date` and `end date` relationships).

Multifield constraints are not yet being generated by this implementation
and will be documented shortly, as they are added.

