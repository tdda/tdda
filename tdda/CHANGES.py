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
"""
