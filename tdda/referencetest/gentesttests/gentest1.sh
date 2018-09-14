CMD='tdda gentest "python 2files.py" 2files one.txt subdir/one.txt stdout stderr nonzeroexit'
tdda gentest "$CMD" meta_2files.py \
                    ref/2files/STDERR \
                    ref/2files/STDOUT \
                    ref/2files/one.txt ref/2files/one.txt1 \
                    STDOUT \
                    STDERR


