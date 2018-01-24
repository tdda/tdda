# -*- coding: utf-8 -*-

#
# We use regex in preference to re when available.
# It has better handling for international character sets.
#
# If you use
#
#     from tdda.rexpy.relib import re, relib
#
# then relib will allow you to know which library is in use.
#


# try:
#     import regex as re
#     relib = 'regex'
# except ImportError:
if 1:
    import re
    relib = 're'




