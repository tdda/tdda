#!/bin/sh
set -x
sh convert1.sh
sh convert2.sh
sh convert3.sh
sh converttopd.sh
sh converttopl.sh
sh converttoplpy.sh
sh examplepl.sh
sh generation1.sh
sh inference1.sh
sh tddaserial1.sh
sh tddaserial2.sh
sh tddaserial3.sh