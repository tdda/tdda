# "XERPY" 1 "%%DATE%%" "%%VERSION%%" "xerpy manual"

## NAME

`xerpy` — generate example strings matching a regular expression

## SYNOPSIS

`xerpy` [`-w` | `-e`] [`-s`] *REX* [*N* [*SEED*]]

## DESCRIPTION

`xerpy` generates random example strings that match a given (simple,
Unix-style) regular expression. It is the inverse of `rexpy(1)`,
which infers regular expressions from example strings.

*REX* is the regular expression to generate strings for.

*N* is the number of strings to generate (default: 1).

*SEED* is the random seed to use (default: derived from the current
time).

## SUPPORTED REGULAR EXPRESSION SYNTAX

`xerpy` understands a Unix-style subset of regular expression syntax:

  - Character classes, e.g. `[a-z0-9]`, including negation
    (`[^0-9]`) and POSIX classes (`[:digit:]`, `[:alpha:]`,
    `[:upper:]`, `[:lower:]`, `[:punct:]`, `[:xdigit:]`, `[:space:]`,
    `[:blank:]`, `[:graph:]`, `[:cntrl:]`).
  - Alternation, e.g. `(cat|dog|bat)`.
  - Quantifiers `*`, `+`, `?` and `{m,n}`.
  - `.`, matching any (printable) character.
  - Escapes `\d` (digits, same as `[0-9]`), `\w` (word characters,
    similar to `[a-zA-Z0-9_]`), `\s` (whitespace), and `\t`, `\r`,
    `\n`, `\f`, `\v`.
  - Unicode-style property classes `\p{...}`/`\P{...}` (negated),
    e.g. `\p{alpha}`, `\p{digit}`, `\p{upper}`, `\p{punct}`.
  - `^` at the start and `$` at the end, as start/end anchors. These
    are effectively always present whether written or not.
  - Alternations without parentheses are treated as if they had
    parentheses, specifically `A|B` is treated as `^(A|B)$` --- not
    `(^A|B$)`.

## OPTIONS

`-w`, `--weighted`  
  Choose among alternation branches (e.g. `a|b|ccc`) weighted by each
  branch's estimated cardinality, so that branches admitting more
  possible strings are chosen more often.

`-e`, `--even`  
  Choose among alternation branches uniformly, regardless of each
  branch's cardinality. This is the default; it explores rare
  branches (e.g. narrow literal alternatives) more than `-w` would.

`-s`, `--seed`  
  Print the random seed used, as `Seed: SEED`, before the generated
  strings.

## EXAMPLES

1) `xerpy '[A-Z]{2}[0-9]{3}'`

Generate one random string matching `[A-Z]{2}[0-9]{3}`.

2) `xerpy '[A-Z]{2}[0-9]{3}' 5`

Generate five such strings.

3) `xerpy '[A-Z]{2}[0-9]{3}' 5 42 -s`

Generate five such strings using seed `42`, printing the seed first.

4) `xerpy '([0-9]|[a-z]{3})' 10 -w`

Generate ten strings, favouring the `[a-z]{3}` branch over `[0-9]`
since it admits many more strings.

## SEE ALSO

`rexpy(1)`
