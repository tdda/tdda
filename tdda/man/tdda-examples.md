# "TDDA EXAMPLES" 1 "January 2026" "3.0" "tdda examples manual"

## NAME

`tdda` examples - Creates example data for TDDA

## SYNOPSIS

`tdda examples`  
`tdda examples` *MODULE*  
`tdda examples` *MODULE* *DIRECTORY*  
`tdda examples` *DIRECTORY*  

## POSITIONAL ARGUMENTS

*MODULE* can be any of:
  - referencetest
  - constraints
  - rexpy
  - gentest
If not specified, all four will be used created.

*DIRECTORY* If specified, the example directories will be
            subdirectories of the specified directory
            (which should exist).


## DESCRIPTION

Write out example code and data for all examples, by default,
or for a particular module if specified.

If no module is specified, examples for all three are written out.

If no output directory is specified, the examples are
written to a subdirectory of the current directory.

## EXAMPLES

a. `tdda examples`  
   Creates all four example directories in `.`

b. `tdda examples gentest`  
   Creates examples-gentest in `.`

c. `tdda examples /tmp/tdda`  
   Creates all four as subdirectories of `/tmp/tdda`

d. `tdda examples rexpy t`  
   Creates examples-rexpy in subdirectory of `./t`



