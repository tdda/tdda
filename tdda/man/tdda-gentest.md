# "TDDA GENTEST" 1 "January 2026" "3.0" "tdda gentest manual"

## NAME

`tdda gentest` - Gentest writes tests, so you don't have to.™

## SYNOPSIS

`tdda gentest`   Runs Wizard

`tdda gentest`   '*SHELL COMMAND*' [*OPTIONS*]
                 [*test_output.py* [*reference files*]]


## DESCRIPTION


## OPTIONS

  -h, --help            show this help message and exit
  -?, --?               Same as -h or --help
  -m, --max-files MAX_FILES
                        Max files to track
  -r, --relative-paths  Show relative paths wherever possible
  -n, --iterations ITERATIONS
                        Number of times to run the command (default 2)
  -O, --no-stdout       Do not generate a test checking output to STDOUT
  -E, --no-stderr       Do not generate a test checking output to STDERR
  -Z, --non-zero-exit   Do not require exit status to be 0
  -C, --no-clobber      Do not overwrite existing test script or reference directory


## EXAMPLES

