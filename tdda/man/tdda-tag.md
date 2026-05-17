# "TDDA TAG" 1 "%%DATE%%" "%%VERSION%%" "tdda tag manual"

## NAME

`tdda tag` — tag tests that failed in the last reference test run

## SYNOPSIS

`tdda tag`

## DESCRIPTION

The `tdda tag` command reads the log of failing tests written by the
most recent logged `tdda.referencetest` run and adds `@tag` decorators
to those tests in their source files. Tagged tests can then be run in
isolation, allowing a rapid edit-test cycle focused on failing
tests. A logged run of `tdda.referencetest` uses `--log-failures` or
(for unittest-style tests only) `-F`.

## WORKFLOW

A typical workflow with `unittest`-style tests (`ReferenceTestCase`) is:


`python tests.py -9      # Remove any existing @tag decorators`  
`python tests.py -F      # Run tests, logging failures`  
`tdda tag                # Add @tag to failing tests`  
`python tests.py -1      # Run only tagged (failing) tests`  


When all tests are passing:

`python tests.py -9      # Remove @tag decorators`  

The equivalent workflow with `pytest` is:

`pytest --untag          # Remove any existing @tag decorators`  
`pytest --log-failures   # Run tests, logging failures`  
`tdda tag                # Add @tag to failing tests`  
`pytest --tagged         # Run only tagged (failing) tests`  

When all tests are passing:

`pytest --untag          # Remove @tag decorators`

## SEE ALSO

`tdda(1)`
