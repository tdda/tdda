#
# Fails to generate 2files test because of non-zero exit code
#
CMD='tdda gentest -r "python 2files.py" 2files . stdout stderr'
tdda gentest "$CMD" meta_2files_fail.py \
                    ref/2files \
                    STDOUT \
                    STDERR \
                    NONZEROEXIT



