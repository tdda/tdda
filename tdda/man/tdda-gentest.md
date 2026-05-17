# "TDDA GENTEST" 1 "%%DATE%%" "%%VERSION%%" "tdda gentest manual"

## NAME

`tdda gentest` — Gentest writes tests, so you don't have to.™

## SYNOPSIS

`tdda gentest`   Runs the Gentest Wizard

`tdda gentest`   '*SHELL COMMAND*' [*OPTIONS*] [*test_output.py*]
               [*REFERENCE_FILE* ...]


## POSITIONAL ARGUMENTS

*SHELL COMMAND* is the command to be tested. It should normally be
enclosed in single quotes. It can be any terminal command — a shell
built-in, a shell script, an R program, a Python program, or anything
else that can be run from the terminal.

*test_output.py* is the name of the Python test script to generate.
If not specified, Gentest derives a name from the command.

*REFERENCE_FILE ...* are optional additional files or directories
that Gentest should monitor for files created or modified during
command execution.

## DESCRIPTION

Gentest will create Python tests, using the tdda's reference-testing
capabilities, for terminal-based programs written in any language.
For example, the shell command can be a built-in shell command
or can run a shell script, an R program,
or of course a Python program.

It has a wizard, invoked just by typing `gentest`, that prompts for
the information it needs before generating the tests.

Alternatively, the command to be tested and optionally other parameters
can all be specified on the command line.

Gentest's tests:
 - Runs the provided command more than once (by default)
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

The test script, when run, executes the command again and
checks that its behaviour is as expected (i.e., is “the same”
as when Gentest ran originally, except for the variations
allowed in the reference test specifications).

## OPTIONS

`-h, --help`            Show this help message and exit  
`-?, --?`               Same as -h or --help  
`-m N, --max-files N`   Max files to track  
`-r, --relative-paths`  Show relative paths wherever possible  
`-n N, --iterations N`  Number of times, `N`, to run the command
                      (default 2)  
`-O, --no-stdout`       Do not generate a test checking output to STDOUT  
`-E, --no-stderr`       Do not generate a test checking output to STDERR  
`-Z, --non-zero-exit`   Do not require exit status to be 0  
`-C, --no-clobber`      Do not overwrite existing test script or  
                      reference directory  
`-N, --no-config`       Use default configuration (ignore `~/.tdda.toml`)  

## EXAMPLES

1) `tdda gentest`  

Runs the Gentest wizard, which presents a dialogue something like this
(where all suggested answers, in square brackets, are accepted by
hitting `RETURN`). (Obviously, this is an improbably simple command test;
it's usually a command to run a script or program.

```
$ tdda gentest
Enter shell command to be tested: echo "Hey, cats!"
Enter name for test script [test_echo__Hey__cats__]:
Check all files written under $(pwd)?: [y]:
Check all files written under (gentest's) $TMPDIR?: [y]:
Enter other files/directories to be checked, one per line, then a blank line:

Check stdout?: [y]:
Check stderr?: [y]:
Exit code should be zero?: [y]:
Clobber (overwrite) previous outputs (if they exist)?: [y]:
Number of times to run script?: [2]:

Running command 'echo "Hey, cats!"' to generate output (run 1 of 2).
Saved (non-empty) output to stdout to /home/tdda/ref/echo__Hey__cats__/STDOUT.
Saved (empty) output to stderr to /home/tdda/ref/echo__Hey__cats__/STDERR.

Running command 'echo "Hey, cats!"' to generate output (run 2 of 2).
Saved (non-empty) output to stdout to /home/tdda/ref/echo__Hey__cats__/2/STDOUT.
Saved (empty) output to stderr to /home/tdda/ref/echo__Hey__cats__/2/STDERR.

Test script written as /home/tdda/test_echo__Hey__cats__.py
Command execution took: 0.022s

SUMMARY:

Directory to run in:        /home/tdda
Shell command:              echo "Hey, cats!"
Test script generated:      /home/tdda/test_echo__Hey__cats__.py
Reference files: (none)
Check stdout:               yes (was 'Hey, cats!\n')
Check stderr:               yes (was empty)
Expected exit code:         0
Clobbering permitted:       yes
Number of times script ran: 2
Number of tests written:    4
```

2) `tdda gentest 'echo "Hey, cats!"' 'test_echo.py' -n 3`  

Same as above except that the command and a custom name for the
test script has been supplied, so the wizard does not run, and the
number of times to run the command has been increased to three.

The test script produced is almost identical except for the number
of times the command is run.

3) `tdda gentest 'diff verifier1.txt verifier2.txt' -Z`  

Gentest will normally fail if the program produces a non-zero exit
code, generally indicating an error. Commands like `diff`, however,
produce a non-zero exit code (1) when there are differences. The `-Z`
option (or `--non-zero-exit`) allows the exit code to be non-zero, and
Gentest generates a test that checks it is the expected value (1, in
this case, if the two verifier files should be different).

## SEE ALSO

`rexpy(1)`, `tdda-diff(1)`
