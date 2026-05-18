# Overview

The `tdda` package provides Python support for
test-driven data analysis
(see [1-page summary](http://stochasticsolutions.com/pdf/TDDA-One-Pager.pdf)
with references, or the [blog](http://www.tdda.info/pages/table-of-contents.html#table-of-contents), or the [book](https://book.tdda.info)).

* :::{image} image/reftest.png
  :width: 150px
  :align: right
  :alt: A white spiral with white text, assertStringCorrect above it, on an orange background.
  :::

  The {py:mod}`tdda.referencetest` library is used to support the creation of
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
     selectively without naming them on the command line. The list of
     failing tests from `tdda.referencetest` runs can also be logged
     automatically, and used to tag failing tests for selective re-running.

* :::{image} image/gentest.png
  :width: 150px
  :align: right
  :alt: A machine with an input hopper with a label "INSERT CODE HERE" and an output chute with a label "COLLECT TESTS HERE". The image is mostly in red with gears in the body of the machine.
  :::

  The [`tdda gentest`](gentest) utility uses {py:mod}`tdda.referencetest`
  to generate tests for any command-line command (scripts and programs
  in any language). These tests can check a variety of kinds of output,
  including output to `stdout`, to `stderr`, and to files, and can
  cope with some variation in outputs (*semantic* correctness).

  ~~.~~

* :::{image} image/discover-verify.png
  :width: 150px
  :align: right
  :alt: A machine with an input hopper with a label "INSERT DATA HERE" and an output chute with a label "COLLECT CONSTRAINTS AND VERIFICATIONS HERE". The image is mostly in blue with gears in the body of the machine.
  :::

  The {py:mod}`tdda.constraints` library and command-line tools are
  used to

   - *discover* constraints from a (Pandas) DataFrame, and write them
     out as JSON ([`tdda discover`](cli.md#tdda-discover) command).
   - *verify* that datasets meet the constraints in the constraints file
     ([`tdda verify`](cli.md#tdda-verify) command).
   - *detect* individual records/values that fail to meet the constraints
     ([`tdda detect`](cli.md#tdda-detect) command).

  As well as data frames in parquet files and flat (CSV) files,
  it also supports tables in a variety of relational databases without extraction.
  There is also a command-line utility for discovering and verifying
  constraints, and detecting failing records.

* :::{image} image/rexpy.png
  :width: 150px
  :align: right
  :alt: A machine with an input hopper with a label "INSERT STRINGS HERE" and an output chute with a label "COLLECT REGEX HERE". The image is mostly in green with gears in the body of the machine.
  :::

  The [`tdda.rexpy`](#tdda.rexpy.rexpy) library is a tool for automatically
  inferring regular expressions from a column in a Pandas DataFrame
  or from a (Python) list of examples.
  There is also a command-line utility for Rexpy ([`rexpy`](cli.md#rexpy) command).

  ~~.~~

  ~~.~~

* :::{image} image/tddadiff.png
  :width: 150px
  :align: right
  :alt: A table showing four columns in two pairs for the same field in two datasets. There are four data rows. Where the data is the same, the values are white. Where they differ, the values from the first dataset are blue and those from the second dataset are red. The background is black.
  :::

  The [`tdda diff`](cli.md#tdda-diff) tool can compare data frames in Parquet
  files and/or flat files and report differences in a visual format
  a bit like a visual diff for text files. Command-line options
  and other specifiers control what differences are reported, and how.

  ~~.~~

  ~~.~~

* :::{image} image/tddaserial.png
  :width: 150px
  :align: right
  :alt: The outline of a JSON object with text replaced with simple bars as placeholders. Teal background with white text.
  :::

  The [`tdda.serial`](cli.md#tdda-serial) format allows the documentation
  of CSV and other flat-file formats in use in the companion
  `.serial` file for more accurate and portable reading and writing
  of flat files. The [`tdda serial`](cli.md#tdda-serial)
  command provides functionality
  for reading and writing `tdda.serial` metadata, as well as for
  reading and writing [CSVW](https://csvw.org)
  and [Frictionless](https://frictionlessdata.io) metadata,
  and for converting between these various metadata formats.

* The [`tdda` utility functions](utils-api.md) provide tools for
  normalization and measurement of Unicode text. This includes:

   - [*Normal Form TK.*](utils-api.md#string-normalization) Normalization
     functions for Normal Form TK, an extension of Unicode Compatibility
     Normalization (normal forms KC and KD).
   - [*Glyph counting*](utils-api.md#unicode-glyph-counting) (as opposed
     to character counting) in strings.
   - [*RFC 9839 support.*](utils-api.md#rfc-9839-character-handling)
     Implementation of RFC 9839's recommendations for removal or replacement
     of deprecated Unicode characters in input data.

Although the library is provided as a Python package, and can be called
through its Python API, it also provides command-line tools, which are
installed when the module is installed.
