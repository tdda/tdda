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

------------------------- dev branch -------------------------
Refactored reporting of differences for files and strings, to take
better account of 'ignore' and 'remove' parameters. It now builds a 'diff'
that will only appear 'different' for lines that are REALLY different, after
any removals and ignores have been collapsed. That diff can also include an
embedded 'raw' diff, which will show ALL the differences, but the main focus
is on showing 'what is different that should not be'.

Also improved reporting of differences when there are different numbers
of lines. It now says what line at which the (effective) differences start
(taking into account removals and ignores).

Also improved reporting of differences when there is no 'actual' file to
compare (just a string in memory, with assertStringCorrect). It now produces
a temporary file containing the 'actual' contents, if there are errors to
report, so that a 'diff' command can be generated in the same way as it does
when there is a file already available.

The ignore_patterns parameter is now treated slightly more strictly than
before, and has had its documentation improved. If you provide an unanchored
regular expression pattern, it now requires that both sides match that
pattern, but it ALSO now requires that the remaining parts, to the left and
right of where the pattern matched, be 'equivalent' if the line is to be
ignored. The two 'left parts' must be equivalent, and the two 'right parts'
must also be equivalent. This 'equivalence' is checked by (recursively)
applying the same logic to these sub-parts.

The ignore_substrings parameter is now treated slightly more strictly than
before. Previously, a line was ignored if it contained any of the ignorable
substrings, in either the actual or the expected. That meant that lines in
the actual data might be being unexpectedly ignored if they start to include
such strings, which probably was not the intent of the test at all. Now,
ignorable substrings only refer to the *expected* data (which is fixed for
the test, and you know exactly what is in it and what is not).

Add comment=None to all constraint constructors.

This allows comments to be added to individual constraints by using
a dictionary for constraint values with keys "value" (for the constraint
value) and "comment" as an ignored string.

Added better support for unittest single-letter command-line option flags,
allowing things like -W, -1 and -0 to be grouped (with themselves, and with
standard unittest options). This means that passing grouped flags such as -1v
or -1W now works as expected with referencetest tests under unittest.

Relaxed limitation that ignore_patterns regex expressions in referencetest tests
couldn't include grouped expressions. Now they can (which is very useful for when
you want to use alternations in expressions, like (a|b)).

------------------------- end of dev branch -------------------------
"""
