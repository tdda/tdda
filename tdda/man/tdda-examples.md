# "TDDA EXAMPLES" 1 "January 2026" "3.0" "tdda examples manual"

## NAME

`tdda` examples - Creates example data for TDDA

## SYNOPSIS

`tdda examples` [OUTDIR]
`tdda examples` [*MODULE...*] [OUTDIR]
`tdda examples` `all` [OUTDIR]

## POSITIONAL ARGUMENTS

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


## DESCRIPTION

Write out example code and data for all examples, by default,
or for a particular module if specified.

If no module is specified, examples for all three are written out.

Examples are always created in subdirectories of the current directory `.`

## EXAMPLES

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


