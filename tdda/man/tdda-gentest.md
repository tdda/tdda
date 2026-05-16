# "TDDA GENTEST" 1 "January 2026" "3.0" "tdda gentest manual"

## NAME

`tdda gentest` - Gentest writes tests, so you don't have to.™

## SYNOPSIS

`tdda gentest`   Runs Wizard

`tdda gentest`   '*SHELL COMMAND*' [*OPTIONS*]
               [*test_output.py*] [*reference files*] [*dir*]


## DESCRIPTION

Gentest will create Python tests, using the tdda's reference-testing
capabilities, for terminal-based programs written in any language.
For example, the shell command can be a built-in shell command
or can run a shell script, an R program,
or of course a Python program.

It has a wizard, invoked just by tying `gentest`, that prompts for
the information it needs before generating the tests.

Alternatively, the command to be tested and optionally other parameters
can all be specified on the command line.

Gentest's tests:
 - Run the provided command more than once (by default)
 - Captures output to `stdout` and `stderr`
 - Captures the exit code
 - Notices any files created in the directory or subdirectories
   or other specified places
 - Uses variations in output and other heuristics to identify
   parts of the output that appear variable and uses `rexpy`
   to write reference tests that only test things that appear
   to be fixed and not system dependent.
 - Writes a Python test script, using `tdda.referencetest`, that contains
   a set of tests of the shell command specified.

The test script can then, of course, be edited by hand.

The test script script, when run, executes the command again and
checks that its behaviour is as expected (i.e., is “the same”
as the runs when Gentest ran originally, except for the variations
allowed in the reference test specifications.

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
  -N, --no-config       Use default configuration (ignore ~/.tdda.toml)


## EXAMPLES

