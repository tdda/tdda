# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
"""1.0.02
Improved documentation to use shorter import forms.

Also bumped version number.

Also planning to tag this with a version to see whether that encourages
readthedocs to add the version properly.

29.05.2018 1.0.03
Add pushv (for maintainer use only) and this CHANGES.py file.

29.05.2018 1.0.04
Correctly cast strings to native strings in check_shell_output.

29.05.2018 1.0.05
Tests for feather are now ignored if pmmif/feather are not installed.

29.05.2018 1.0.06
Windows fixes.

31.05.2018 1.0.07
Fix for UTF-8 encoding in subprocesses on Windows.

Also added documentation on setting up fonts on Windows to display
ticks and crosses correctly.

6.06.2018 1.0.08
Improved metadata in TDDA files.

11.06.2018 1.0.09
Add support for postloadhook and postdicthook.

25.07.2018 1.0.10
Minor bug fixes.

 - Fuzzy verification of 'min' constraint was printing out the type of the col.
 - Typo in documentation of the properties available in a Verification result.
 - Verification of 'rex' constraint was not checking that the field exists.

26.07.2018 1.0.11
Fixed bug in pandas detect; it wasn't detecting min/max length constraints.

Also fixed issue with pandas CSV file reader; it has problems reading files
that have stuttered quotes and which also have escaped content. It now
notices if that has gone wrong, and has another try.

26.07.2018 1.0.12
minor refactoring and comments

1.08.2018 1.0.13
Now accepts 'false' as a valid specification value for no-duplicates.

Also improved the error message you get if you provide invalid specifications.
Also suppressed pandas warning about nanoseconds on conversion.

1.08.2018 1.0.14
Ignore epsilon for date min/max (rather than crashing).

This probably isn't ideal, but to make it better we'd need to decide
on what epsilon should mean for dates, which is not obvious.

13.08.2018 1.0.15
Change use of re.U (UNICODE) to re.UNICODE | re.DOTALL.

This means that dot actually matches any character.
The Python documentation claims that without this any character except
newline is matched, but it appears that some other characters are
also not matched without re.DOTALL, including a non-breaking space (0x80).

18.09.2018 1.0.16
referencetest class now exports TaggedTestLoader for convenience.

18.09.2018 1.0.17
TestLoader now takes an optional 'printer' parameter to control how -0 works.

18.09.2018 1.0.18
Renamed tdda.referencetest method assertFileCorrect -> assertTextFileCorrect.

The original name is still available for backwards compatibility, but
is deprecated.

19.09.2018 1.0.19
Added tdda.referencetest method assertBinaryFileCorrect.
Also fixed some issues with tdda.referencetest ignore_patterns method.

19.09.2018 1.0.20
Added test files so that all the new tests will pass.

28.02.2019 1.0.21
Changed 'test' command to from 'this' Python rather than a new Python.

Previously, the 'test' command (run with 'tdda test') ran in a subshell
using an os.system call. In order to do this, we used sys.executable()
to find (ostensibly) the path to the running version of Python.

It transpires, however, that sys.executable() does not always return
the path to the running Python...and indeed sometimes returns a path
that does not exist. We now, therefore, simply run the tests in the
current Python, by calling the (new) function 'testall', now used
by main() in tdda.testtdda.py.

13.03.2019 1.0.22
Fix for fuzzy min/max comparison on date columns, previously crashing.

Also fixed issue with problems, on some platforms, with the 'tdda examples'
command, for non-ascii example files. It had already had support for doing
this, but it wasn't always working. Now it's much more bullet-proof.

Also, it no longer generates warnings for unrecognised keys in the input
.tdda file (on verify and detect), for keys with names that begin with '#'.
This gives a mechanism for 'commented out' items in the file (which you
could always do, but you'd get annoying warnings, which now you no longer
get).

Also added some examples of 'detect' in the constraints examples and README.

Also added some examples for the 'accounts' banking datasets for constraints,
and included this new dataset as part of the standard examples you get if
you run 'tdda examples'.

Also fixed typo in link to 1-pager pdf in the documentation.

Added tests for accounts-based constraints examples.
Also, copying examples now unzips the file.

18.03.2019 1.0.23
Fixed tests to pass under Python 3.7.2.

The standard re.escape method changed after python version 3.7.1 so that it
only escapes characters that would otherwise be treated as having special
meaning within a regular expression. So the tests now need to allow BOTH
outputs to be considered correct. It's less easy than you'd imagine to work
out exactly what subversion the behaviour changed in.

Small fix to one test to ensure it still works in Pythons 2.7 & 3.6.

Fixed reftest example to use ignore_substrings rather than ignore_patterns
(as a result of the change to semantics of ignore_patterns in 1.0.19).

Added API examples for reference tests using accounts data.
"""
