#!/bin/sh
tdda discover small.csv small.json > discover-small.stdout 2> discover-small.stderr
tdda verify small.csv small.json > verify-small.stdout 2> verify-small.stderr
tdda detect small.csv small.json detect-small-bads.csv > detect-small.stdout 2> detect-small.stderr

# Fails for record 3, fields a and c: standard verify, detect
tdda verify small.csv small-lo.json > verify-small-lo.stdout 2> verify-small-lo.stderr
tdda detect small.csv small-lo.json detect-small-lo-bads.csv > detect-small-lo.stdout 2> detect-small-lo.stderr

# Fails for record 3, fields a and c: standard detect -f
# Suppresses field b_values_ok
tdda detect -f small.csv small-lo.json detect-small-lo-f-bads.csv > detect-small-lo-f.stdout 2> detect-small-lo-f.stderr

# Fails for record 3, fields a and c: standard detect --no-original-fields
# HAS NO EFFECT
tdda detect --no-original-fields small.csv small-lo.json detect-small-lo-nof-bads.csv > detect-small-lo-nof.stdout 2> detect-small-lo-nof.stderr


