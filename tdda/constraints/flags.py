# -*- coding: utf-8 -*-

"""
Helpers for command-line option flags for discover and verify
"""

import argparse
import sys


DISCOVER_HELP = '''
Optional flags are:

  * -r or --rex
      Include regular expression generation. Disabled by default.
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
      Use this value of epsilon for fuzziness in comparing numeric values.
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
      Use this value of epsilon for fuzziness in comparing numeric values.
  * --write-all
      Include passing records in the output.
  * --per-constraint
      Write one additional column per failing constraint, to show if a
      constraint passed or failed, as well as the n_failures
      total column for each row. This is set by default.
  * --no-per-constraint
      Disable the --per-constraint flag, so that the only constraint-based
      column written out is the nfailures field.
  * --no-original-fields
      Do not write out any of the original columns. By default, all of the
      original columns are written out, unless you use --output-fields.
  * --output-fields FIELD1 FIELD2 ...
      Specify original columns to write out.
  * --interleave
      In the output, place the verification fields immediately after
      the original field to which they correspond.
  * --index
      Include a row-number index in the output file.
      The row number is automatically included if no output fields are
      specified. Rows are usually numbered from 1, unless the
      input file already has an index.

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
    parser.add_argument('-7', '--ascii', action='store_true',
                        help='report without using special characters')
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
    parser.add_argument('-t', '--type_checking', choices=['strict', 'sloppy'],
                        help='"sloppy" means consider all numeric types '
                             'equivalent')
    parser.add_argument('-epsilon', '--epsilon', type=float,
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
    parser.add_argument('-t', '--type_checking', choices=['strict', 'sloppy'],
                        help='"sloppy" means consider all numeric types '
                             'equivalent')
    parser.add_argument('-epsilon', '--epsilon', type=float,
                        help='epsilon fuzziness')
    parser.add_argument('--write-all', action='store_true',
                        help='Include passing records')
    parser.add_argument('--per-constraint', action='store_true',
                        help='Write one flag column per failing constraint '
                             'in addition to n_failures. Set by default.')
    parser.add_argument('--no-per-constraint', action='store_true',
                        help='Do not write out any per-constraint flag columns')
    parser.add_argument('--no-output-fields', action='store_true',
                        help='Do not write out any original fields in the '
                             'output. By default, all original columns will '
                             'be included.')
    parser.add_argument('--output-fields', nargs='*',
                        help='Specify original columns to write out.')
    parser.add_argument('--interleave', action='store_true',
                        help='Interleave ok columns with original fields.')
    parser.add_argument('--index', action='store_true',
                        help='Include a row-number index in the output file '
                             'when detecting. Rows are usually numbered from '
                             '1, unless the input file already has an index.')
    parser.add_argument('--int', dest='boolean_ints', action='store_true',
                        help='Write out boolean fields as integers, with '
                             '1 for true and 0 for false.')
    return parser


def verify_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print('Unexpected arguments %s\n' % ' '.join(more),
              parser.epilog, file=sys.stderr)
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
    if flags.type_checking is not None:
        params['type_checking'] = flags.type_checking
    if flags.epsilon is not None:
        params['epsilon'] = float(flags.epsilon)
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
    if flags.per_constraint and flags.no_per_constraint:
        print('You must not specify both --per-constraint and '
              '--no-per-constraint.', file=sys.stderr)
        sys.exit(1)
    if flags.output_fields and flags.no_output_fields:
        print('You must not specify both --output-fields and '
              '--no-output-fields.', file=sys.stderr)
        sys.exit(1)
    if flags.ascii:
        params['ascii'] = True
    if flags.type_checking is not None:
        params['type_checking'] = flags.type_checking
    if flags.epsilon is not None:
        params['epsilon'] = float(flags.epsilon)
    if flags.write_all:
        params['write_all'] = True
    if not flags.no_per_constraint:
        params['per_constraint'] = True
    if flags.index:
        params['index'] = True
    if flags.boolean_ints:
        params['boolean_ints'] = True

    if flags.output_fields is not None:
        params['output_fields'] = flags.output_fields
    elif not flags.no_output_fields:
        params['output_fields'] = []

    if flags.interleave:
        params['interleave'] = True
    params['in_place'] = False  # Only applicable in API case
    params['report'] = 'records'
    return flags

