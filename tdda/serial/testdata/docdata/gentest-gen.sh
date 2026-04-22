#!/bin/sh
set -x
tdda gentest 'sh convert1.sh'
tdda gentest 'sh convert2.sh'
tdda gentest 'sh convert3.sh'
tdda gentest 'sh converttopd.sh'
tdda gentest 'sh converttopl.sh'
tdda gentest 'sh converttoplpy.sh'
tdda gentest 'sh examplepl.sh'
tdda gentest 'sh generation1.sh'
tdda gentest 'sh inference1.sh'
tdda gentest 'sh tddaserial1.sh'
tdda gentest 'sh tddaserial2.sh'
tdda gentest 'sh tddaserial3.sh'
