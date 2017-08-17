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
  * -epsilon E
      Use this value of epsilon for fuzziness in comparing numeric values
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
    parser.add_argument('-epsilon', nargs=1, help='epsilon fuzziness')
    return parser


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
        params['epsilon'] = flags.epsilon[0]
    return flags

