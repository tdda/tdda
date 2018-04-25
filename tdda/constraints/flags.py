# -*- coding: utf-8 -*-

"""
Helpers for command-line option flags for discover and verify
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import argparse
import sys


DISCOVER_HELP = '''
Optional flags are:

  * -r or --rex
      Include regular expression generation
  * -R or --norex
      Exclude regular expression generation (the default)
'''

VERIFY_HELP = '''
Optional flags are:

  * -a, --all
      Report all fields, even if there are no failures
  * -f, --fields
      Report only fields with failures
  * -c, --constraints
      Report only individual constraints that fail.  Not yet implemented.
  * -1, --oneperline
      Report each constraint failure on a separate line.  Not yet implemented.
  * -7, --ascii
      Report in ASCII form, without using special characters.
  * --epsilon E
      Use this value of epsilon for fuzziness in comparing numeric values
  * --detect OUTPATH
      Write failing records (by default) to OUTPATH
  * --detect-write-all
      Include passing records when detecting
  * --detect-per-constraint
      Write one column per failing constraint when detecting, as well as
      the n_failures total column for each row.
  * --detect-output-fields FIELD1,FIELD2
      Specify original columns to write out when detecting.
      If used with no field names, all original columns will be included.
  * --detect-rownumber
      Include a row-number in the output file when detecting.
      The row number is automatically included if no output fields are
      specified. Rows are numbered from 0.

'''

def discover_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda discover',
                                     epilog=usage + DISCOVER_HELP,
                                     formatter_class=formatter)
    parser.add_argument('-?', '--?', action='help',
                        help='same as -h or --help')
    parser.add_argument('-r', '--rex', action='store_true',
                        help='include regular expression generation')
    parser.add_argument('-R', '--norex', action='store_true',
                        help='exclude regular expression generation')
    return parser


def discover_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print(parser.epilog, file=sys.stderr)
        sys.exit(1)
    params['inc_rex'] = flags.rex
    return flags


def verify_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda verify',
                                     epilog=usage + VERIFY_HELP,
                                     formatter_class=formatter)
    parser.add_argument('-?', '--?', action='help',
                        help='same as -h or --help')
    parser.add_argument('-a', '--all', action='store_true',
                        help='report all fields, even if there are '
                             'no failures')
    parser.add_argument('-f', '--fields', action='store_true',
                        help='report only fields with failures')
    parser.add_argument('-c', '--constraints', action='store_true',
                        help='report only individual constraints that fail')
    parser.add_argument('-1', '--oneperline', action='store_true',
                        help='report each constraint failure on a '
                             'separate line')
    parser.add_argument('-7', '--ascii', action='store_true',
                        help='report without using special characters')
    parser.add_argument('-type_checking', action='store_true',
                        help='strict or sloppy')
    parser.add_argument('-epsilon', '--epsilon', nargs=1,
                        help='epsilon fuzziness')
    parser.add_argument('--detect', nargs=1,
                        help='Write failing records (by default) to OUTPATH')
    parser.add_argument('--detect-write-all', action='store_true',
                        help='Include passing records when detecting')
    parser.add_argument('--detect-per-constraint', action='store_true',
                        help='Write one column per failing constraint '
                             'when detectin\n, in addition to n_failures.')
    parser.add_argument('--detect-output-fields', nargs='*',
                        help='Specify original columns to write out when '
                             'detecting. If used with no field names, then '
                             'all original columns will be included.')
    parser.add_argument('--detect-rownumber', action='store_true',
                        help='Include a row-number in the output file when '
                             'detecting. Rows are numbered from 0.')

    return parser


def detect_parser(usage=''):
    return verify_parser(usage=usage)


def verify_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print(parser.epilog, file=sys.stderr)
        sys.exit(1)
    params.update({
        'report': 'all',
        'one_per_line': False,
        'ascii': False,
    })
    if flags.all:
        params['report'] = 'all'
    elif flags.fields:
        params['report'] = 'fields'
    elif flags.constraints:
        params['report'] = 'constraints'
    if flags.oneperline:
        params['one_per_line'] = True
    if flags.ascii:
        params['ascii'] = True
    if flags.type_checking:
        params['type_checking'] = True
    if flags.epsilon:
        params['epsilon'] = float(flags.epsilon[0])
    if flags.detect:
        params['detect_outpath'] = flags.detect[0]
    if flags.detect_write_all:
        params['detect_write_all'] = True
    if flags.detect_per_constraint:
        params['detect_per_constraint'] = True
    if flags.detect_rownumber:
        params['detect_rownumber'] = True
    if flags.detect_output_fields is not None:
        params['detect_output_fields'] = flags.detect_output_fields
    params['detect_in_place'] = False  # Only applicable in API case
    return flags


def detect_flags(parser, args, params):
    return verify_flags(parser, args, params)

