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
  * -7, --ascii
      Report in ASCII form, without using special characters.
  * --epsilon E
      Use this value of epsilon for fuzziness in comparing numeric values
'''

DETECT_HELP = '''
Optional flags are:

  * -a, --all
      Report all fields, even if there are no failures
  * -f, --fields
      Report only fields with failures
  * -7, --ascii
      Report in ASCII form, without using special characters.
  * --epsilon E
      Use this value of epsilon for fuzziness in comparing numeric values
  * --write-all
      Include passing records when detecting
  * --per-constraint
      Write one column per failing constraint when detecting, as well as
      the n_failures total column for each row.
  * --output-fields FIELD1,FIELD2
      Specify original columns to write out when detecting.
      If used with no field names, all original columns will be included.
  * --rownumber
      Include a row-number in the output file when detecting.
      The row number is automatically included if no output fields are
      specified. Rows are usually numbered from 1, unless the input file
      has a special index.

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
    parser.add_argument('-7', '--ascii', action='store_true',
                        help='report without using special characters')
    parser.add_argument('-type_checking', action='store_true',
                        help='strict or sloppy')
    parser.add_argument('-epsilon', '--epsilon', nargs=1,
                        help='epsilon fuzziness')
    return parser


def detect_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda detect',
                                     epilog=usage + DETECT_HELP,
                                     formatter_class=formatter)
    parser.add_argument('-?', '--?', action='help',
                        help='same as -h or --help')
    parser.add_argument('-a', '--all', action='store_true',
                        help='report all fields, even if there are '
                             'no failures')
    parser.add_argument('-f', '--fields', action='store_true',
                        help='report only fields with failures')
    parser.add_argument('-7', '--ascii', action='store_true',
                        help='report without using special characters')
    parser.add_argument('-type_checking', action='store_true',
                        help='strict or sloppy')
    parser.add_argument('-epsilon', '--epsilon', nargs=1,
                        help='epsilon fuzziness')
    parser.add_argument('--write-all', action='store_true',
                        help='Include passing records')
    parser.add_argument('--per-constraint', action='store_true',
                        help='Write one column per failing constraint '
                             'in addition to n_failures')
    parser.add_argument('--output-fields', nargs='*',
                        help='Specify original columns to write out. '
                             'If used with no field names, then '
                             'all original columns will be included')
    parser.add_argument('--rownumber', action='store_true',
                        help='Include a row-number in the output file when '
                             'detecting. Rows are usually numbered from 1, '
                             'unless the input file has a special index.')
    parser.add_argument('--int', dest='boolean_ints', action='store_true',
                        help='Write out boolean fields as integers, with '
                             '1 for true and 0 for false.')
    return parser


def verify_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print(parser.epilog, file=sys.stderr)
        sys.exit(1)
    params.update({
        'report': 'all',
        'ascii': False,
    })
    if flags.all:
        params['report'] = 'all'
    elif flags.fields:
        params['report'] = 'fields'
    if flags.ascii:
        params['ascii'] = True
    if flags.type_checking:
        params['type_checking'] = True
    if flags.epsilon:
        params['epsilon'] = float(flags.epsilon[0])
    return flags


def detect_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print(parser.epilog, file=sys.stderr)
        sys.exit(1)
    params.update({
        'report': 'records',
        'ascii': False,
    })
    if flags.all:
        params['report'] = 'all'
    elif flags.fields:
        params['report'] = 'records'
    if flags.ascii:
        params['ascii'] = True
    if flags.type_checking:
        params['type_checking'] = True
    if flags.epsilon:
        params['epsilon'] = float(flags.epsilon[0])
    if flags.write_all:
        params['write_all'] = True
    if flags.per_constraint:
        params['per_constraint'] = True
    if flags.rownumber:
        params['rownumber'] = True
    if flags.boolean_ints:
        params['boolean_ints'] = True
    if flags.output_fields is not None:
        params['output_fields'] = flags.output_fields
    params['in_place'] = False  # Only applicable in API case
    params['report'] = 'records'
    return flags

