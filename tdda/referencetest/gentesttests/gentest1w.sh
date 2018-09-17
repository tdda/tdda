#
# Generates 2files test successfully using wizard.
#
# Currently requires STDOUT test to get exclusions added for
# command timings, because it is not generated automatically.
#

CMD='tdda gentest < gentest1w.input'
tdda gentest "$CMD" meta_2files_wizard.py \
                    ref/2files_wizard \
                    STDOUT \
                    STDERR
