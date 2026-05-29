# Examples of using tdda.rexpy

Rexpy automatically constructs regular expressions from data.
Regular expressions are powerful but hard to write and read.
Rexpy infers them for you from examples of strings that should match.

Rexpy is intended for strings with structure: identifiers, postcodes,
UUIDs, phone numbers, email addresses, version numbers, and so on.
It is not useful for free text.

For all of these examples, run commands on the command line after
cd'ing to this directory.

## Command-line examples

### Simple identifiers

The file `headed-ids.txt` contains a column of structured IDs with
a header line:

    ID
    123-AA-971
    12-DQ-802
    198-AA-045
    1-BA-834

Use `-h` to discard the header, then rexpy infers the pattern:

    rexpy -h headed-ids.txt

This should produce:

    ^[0-9]{1,3}\-[A-Z]{2}\-[0-9]{3}$

### Postcodes

    rexpy postcodes.txt

UK postcodes have a regular structure — rexpy captures it:

    ^[A-Z]{1,2}[0-9]{1,2} [0-9][A-Z]{2}$

### UUIDs

    rexpy uuids.txt

UUIDs are highly regular, so rexpy produces a precise pattern:

    ^[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}$

### User-agent strings

    rexpy agents9.txt

User-agent strings are structured but extremely varied. Rexpy produces
one regex per distinct pattern — with only 9 strings it cannot
generalise. This illustrates the limit: rexpy works well when strings
share a common structure, but not when they are all different.

### Reading from standard input

You can also pipe strings directly to rexpy:

    echo -e "2024-01-15\n2024-03-22\n2023-11-07" | rexpy

## Python API examples

### ids.py — basic usage

    python ids.py

Uses `rexpy.extract()` on a list of strings.

### pandas_ids.py — Pandas integration

    python pandas_ids.py

Uses `rexpy.pdextract()` to infer regexes from Pandas Series,
including combining multiple columns to find a shared pattern.

## Command-line flags

Run `rexpy --help` for full options. Useful flags include:

    -h, --header     Discard the first line (treat it as a header)
    -u, --underscore Allow underscore as a letter (useful for identifiers)
    -d, --dot        Allow dot as a letter (useful for identifiers)
    -g, --group      Add capture groups around variable parts of the regex
