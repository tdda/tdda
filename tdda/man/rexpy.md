# "REXPY" 1 "%%DATE%%" "%%VERSION%%" "rexpy manual"

## NAME

`rexpy` — infer regular expressions from example strings

## SYNOPSIS

`rexpy` [*FLAGS*] [*INPUTFILE* [*OUTPUTFILE*]]

## DESCRIPTION

`rexpy` reads a list of strings (one per line) and infers one or more
regular expressions that characterize them.

If *INPUTFILE* is provided it should contain one string per line;
otherwise lines are read from standard input.

If *OUTPUTFILE* is provided, the regular expressions found will be
written there (one per line); otherwise they will be printed to
standard output.

## OPTIONS

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

## SEE ALSO

`tdda(1)`, `tdda-discover(1)`
