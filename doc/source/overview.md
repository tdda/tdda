# Overview

The `tdda` package provides Python support for
test-driven data analysis
(see [1-page summary](http://stochasticsolutions.com/pdf/TDDA-One-Pager.pdf)
with references, or the [blog](http://www.tdda.info/pages/table-of-contents.html#table-of-contents), or the [book](https://book.tdda.info)).

* The {py:mod}`tdda.referencetest` library is used to support the creation of
  *reference tests*, based on either `unittest` or `pytest`.

   - *Semantic Equivalence.* Reference tests allow checking outputs
     for semantic equivalence rather than identical objects.
     Tests can be parameterized to specify what is allowed to vary.
   - *File-based Comparisons.* Strings and data frames can be compared
     against reference outputs in files. When tests fail, the in-memory
     datastructures are written to file and suitable `diff` commands
     proposed.
   - *Automatic Rewriting of Reference Results.* When behaviour is updated,
     reference results in file can be selectively rewritten after verification.
   - *Tagging of Tests.* Tests and test classes can be tagged, and run
     selectively without naming them on the command line.

* The [`tdda gentest`](gentest) utility uses {py:mod}`tdda.referencetest`
  to generate tests for any command-line command (scripts and programs
  in any language). These tests can check a variety of kinds of output,
  including output to `stdout`, to to `stderr`, and to files, and can
  cope with some variation in outputs (&semantic* correctness).

* The {py:mod}`tdda.constraints` library and command-line tools are
  used to

   - *discover* constraints from a (Pandas) DataFrame, and write them
     out as JSON (`tdda discover` command).
   - *verify* that datasets meet the constraints in the constraints file
     (`tdda verify` command).
   - *detect* individual records/values that fail to meet the constraints
     (`tdda detect` command).

  As well as data frames in parquet files and flat (CSV) files,
  it also supports tables in a variety of relation databases without extraction.
  There is also a command-line utility for discovering and verifying
  constraints, and detecting failing records.

* The [`tdda.rexpy`](#tdda.rexpy.rexpy) library is a tool for automatically
  inferring regular expressions from a column in a Pandas DataFrame
  or from a (Python) list of examples.
  There is also a command-line utility for Rexpy (`rexpy` command).

* The [`tdda diff`](cli.md#tdda-diff) tool can compare dataframes in Parquet
  file and/or flat files and report differences. Command-line options
  and other specifiers control what differences are reported, and how.

* The [`tdda.serial`](cli.md#tdda-serial) format allows the documentation
  of CSV and other flat-file formats in use in the companion
  `.serial` file for more accurate and portable reading and writing
  of flat files. The `tdda serial` command provides functionality
  for reading and writing `tdda.serial` metadata, as well as for
  reading and writing [CSVW](https://csvw.org)
  and [Frictionless](https://frictionlessdata.io) metadata,
  and for converting between these various metadata formats.

Although the library is provided as a Python package, and can be called
through its Python API, it also provides command-line tools, which are
installed when the module is installed.

