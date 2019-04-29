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
rm -rf [a-z]*

echo 'Recreating output dir'
mkdir output

echo 'Generate test for copying examples'
tdda gentest 'tdda examples constraints' test_examples.py . STDOUT STDERR

echo 'Generate test for initial discover command'
tdda gentest 'tdda discover -r INPUTS/testdata/accounts1k.csv output/accounts1k.tdda' test_discover1k.py . STDOUT STDERR

echo 'Generate test for successful verify command'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts1k.csv INPUTS/testdata/accounts1k.tdda' test_verify.py . STDOUT STDERR

echo 'Generate test for unsuccessful verify command'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1k.tdda' test_verify_fail.py . STDOUT STDERR

echo 'Generate test for unsuccessful verify command with edited file'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda' test_verify_fail2.py . STDOUT STDERR

echo 'Generate test for detect command command with 11 failing records'
tdda gentest 'tdda detect -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda output/bads.csv' test_detect.py . STDOUT STDERR

echo 'Generate test for discover on 25k data'
tdda gentest 'tdda discover INPUTS/testdata/accounts25k.csv output/accounts25k.tdda' test_discover2.py . STDOUT STDERR

echo 'Generate test for second successful verify command'
tdda gentest 'tdda verify -7 INPUTS/testdata/accounts1k.csv INPUTS/accounts25k.tdda' test_verify2.py . STDOUT STDERR

rm -rf constraints_examples output/*
