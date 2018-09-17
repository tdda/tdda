#
# Generates 2files test successfully, specifying non-zero exit code is allowed
#
# Currently requires STDOUT test to get exclusions added for
# command timings, because it is not generated automatically.
#

CMD='tdda gentest "python 2files.py" 2files . stdout stderr nonzeroexit'
tdda gentest "$CMD" meta_2files.py \
                    ref/2files \
                    STDOUT \
                    STDERR


