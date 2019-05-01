#
# This script shows how the gentest tests for the constraints examples
# were generated. It should not need to be run again unless something
# changes, (correctly) causing these tests to fail.
#
# Depending on what changes, re-running this might or might not
# then be the best way forward.
#
# (Using referencetest's --write-all functionality might be enough/better.)
#

echo "Cleaning out anything that shouldn't be here"
if [ ! -f "GENERATE_TESTS.sh" ]
then
    echo "You are in the wrong directory!" 1>&2
    exit 1
fi
rm -rf [a-z]*

echo 'Generate test for copying examples'
tdda gentest 'tdda examples constraints $TMPDIR' test_examples.py . STDOUT STDERR

echo 'Generate test for initial discover command'
tdda gentest 'tdda discover -r INPUTS/testdata/accounts1k.csv $TMPDIR/accounts1k.tdda' test_discover1k.py . STDOUT STDERR

echo 'Generate test for successful verify command'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts1k.csv INPUTS/testdata/accounts1k.tdda' test_verify.py . STDOUT STDERR

echo 'Generate test for unsuccessful verify command'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1k.tdda' test_verify_fail.py . STDOUT STDERR

echo 'Generate test for unsuccessful verify command with edited file'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda' test_verify_fail2.py . STDOUT STDERR

echo 'Generate test for detect command command with 11 failing records'
tdda gentest 'tdda detect -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda $TMPDIR/bads.csv' test_detect.py . STDOUT STDERR

echo 'Generate test for discover on 25k data'
tdda gentest 'tdda discover INPUTS/testdata/accounts25k.csv $TMPDIR/accounts25k.tdda' test_discover25k.py . STDOUT STDERR

echo 'Generate test for second successful verify command'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts1k.csv INPUTS/accounts25k.tdda' test_verify2.py . STDOUT STDERR

cp TEST_ALL_UC.py testall.py

