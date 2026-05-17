# "TDDA CONFIG" 1 "%%DATE%%" "%%VERSION%%" "tdda config manual"

## NAME

`tdda config` — Shows config settings

## SYNOPSIS

`tdda config [--annotated|-a] [--current|-c] [--default|-d] [--file|-f]`  
`tdda config [--annotated|-a] current|default|file`

## DESCRIPTION

Shows configuration information. Use:

`-c`, `--current`, or `current` for the current configuration  
`-d`, `--default`, or `default` for the default configuration  
`-f`, `--file`, or `file` for the configuration file location and contents.

With no argument, it shows the current configuration.

Use `-a` or `--annotated` with any of the above to show allowed values
alongside each parameter.

## EXAMPLES

`tdda config`  
`tdda config -c`  
`tdda config -d`  
`tdda config -f`


## PARAMETERS

### `null_rep`
Used to show nulls in some contexts.  
**Default:** `"∅"`  
**Allowed:** Any string
### `colour`
Controls whether output is colourized.  
**Default:** `true`  
**Allowed:** `true`, `false`
### `engine`
Controls whether pandas or polars is used for CSV files by default.  
**Default:** `"pandas"`  
**Allowed:** `"pandas"`, `"polars"`
### `pandas_backend`
Controls default backend for CSV loading etc.  
**Default:** `"numpy_nullable"`  
**Allowed:** `"numpy_nullable"` (or `"n"`), `"pyarrow"` (or `"a"`), `"original"` (or `"o"`)

## PARAMETERS (referencetest)

### `left_colour`
Colour for left (actual) side of diffs.  
**Default:** `"red"`  
**Allowed:** A named ANSI colour (red, bright_red etc.) or an RGB hex colour with leading # such as #FF0000 for pure red. Interpreted by the rich library.
### `right_colour`
Colour for right (expected) side of diffs.  
**Default:** `"green"`  
**Allowed:** A named ANSI colour (red, bright_red etc.) or an RGB hex colour with leading # such as #FF0000 for pure red. Interpreted by the rich library.
### `failure_colour`
Colour used to highlight failures.  
**Default:** `"red"`  
**Allowed:** A named ANSI colour (red, bright_red etc.) or an RGB hex colour with leading # such as #FF0000 for pure red. Interpreted by the rich library.
### `mono`
Use bold instead of colour for diffs.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `bw`
Black and white mode: no colour or bold.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `left_prefix`
Prefix string for left (actual) diff lines.  
**Default:** `"< "`  
**Allowed:** Any string
### `right_prefix`
Prefix string for right (expected) diff lines.  
**Default:** `"> "`  
**Allowed:** Any string
### `vertical`
Show diffs vertically rather than side by side.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `force_val_prefixes`
Always show left/right prefixes on diff lines.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `type_checking`
How strictly to check types in reference test comparisons.  
**Default:** `"strict"`  
**Allowed:** `"strict"`, `"medium"`, `"loose"`
### `log_failures`
Log failing test IDs to file for use with `tdda tag`.  
**Default:** `false`  
**Allowed:** `true`, `false`

## PARAMETERS (constraints)

### `interleave`
Interleave pass and fail results in verify output.  
**Default:** `true`  
**Allowed:** `true`, `false`
### `per_constraint`
Report results per constraint rather than per field.  
**Default:** `true`  
**Allowed:** `true`, `false`
### `detect_passes`
Include passing fields in detect output.  
**Default:** `true`  
**Allowed:** `true`, `false`
### `report_formats`
List of additional report formats to generate.  
**Default:** `[]`  
**Allowed:** Any subset of `"html"`, `"md"`, `"txt"`, `"json"`, `"yaml"`, `"toml"`
### `write_all_records`
Write all records to detect output, not just failures.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `int_bools`
Use integers (0/1) rather than booleans in detect output.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `verify_required_fields`
Verify that all required fields are present.  
**Default:** unset  
**Allowed:** `true`, `false`
### `verify_allowed_fields`
Verify that no fields are present outside the allowed set.  
**Default:** unset  
**Allowed:** `true`, `false`
### `write_required_fields`
Discover should include the required-fields constraint.  
**Default:** `false`  
**Allowed:** `true`, `false`
### `write_allowed_fields`
Discover should include an allowed-fields constraint.  
**Default:** `false`  
**Allowed:** `true`, `false`

## PARAMETERS (tddadiff)

### `type_checking`
How strictly to check types when comparing dataframes.  
**Default:** `"medium"`  
**Allowed:** `"strict"`, `"medium"`, `"loose"`
### `find_md`
Infer metadata when comparing dataframes with tdda diff.  
**Default:** `true`  
**Allowed:** `true`, `false`

## PARAMETERS (serial)

### `md_inpath`
Path(s) to search for serial metadata files; relative paths are resolved relative to the CSV file.  
**Default:** `"./_write.serial"`




