# -*- coding: utf-8 -*-

"""
Helpers for command-line option flags for discover and verify
"""

import argparse
import os
import sys

from tdda.state import set_load
from tdda.utils import error
from tdda.commonflags import add_pandas_flags, process_pandas_flags


def help_defaults(help=True, seven=True, colour=True, config=True,
                  epsilon=False):
    out = []
    if epsilon:
        out.append('''
  * --epsilon E
      Use this value of epsilon for fuzziness in comparing numeric values.
''')
    if seven:
        out.append('''
  * -7, --ascii
      Report in ASCII form, without using special characters.
''')
    if colour:
        out.append('''
  * --colour
      Coloured output
  * --no-colour
      Monochrome output
''')
    if config:
        out.append('''
  * -N, --no-config
      Do not configure using ~/tdda.toml: use all defaults
''')
    return ''.join(o.rstrip() for o in out) + '\n'

    if help:
        out.append('''
  * -?, --help
      Show help
''')
    return ''.join(o.rstrip() for o in out) + '\n'


VERIFY_FIELDS_HELP = '''
  * --vrf --verify-required-fields
      Force Verification of required field
  * --vaf --verify-allowed-fields
      Force verification of allowed fields
  * --varf, --vraf
      Force verification of allowed and required fields
  * --no-vr
      Force no verification of not verify required fields
  * --no-va
      Force no verification of allowed fields
  * --no-varf, --no-vraf
      Force no verification  of allowed and required fields
'''


DISCOVER_HELP = '''
Optional flags are:

  * -x or --rex
      Include regular expression generation. Disabled by default.
  * -X or --no-rex
      Exclude regular expression generation (the default)
  * -g or --group-rex
      Group regular expressions when generated (the default)
  * -G or --no-group-rex
      Do not group regular expressions when generated
  * -r or --report FORMAT1 FORMAT2 ...
      Write constraints reports in the formats listed. Allowed formats
      are: html, text, txt, json, yaml, toml, mmarkdown, and md.
  * -o or --report-path PATH''' + help_defaults()


VERIFY_HELP = ('''
Optional flags are:

  * -a, --all
      Report all fields, even if there are no failures
  * -f, --fields
      Report only fields with failures
'''
      + VERIFY_FIELDS_HELP
      + help_defaults(epsilon=True)
)


DETECT_HELP = ('''
Optional flags are:

  * -o, --report-path PATH
      Path to which to write reports.
      Unnecessary when records are written to file, but needed when
      writing detected records to databases.
      Extension does not matter (will be chosen to match report formats).
  * -a, --all
      Report all fields, even if there are no failures
  * -f, --fields
      Report only fields with failures
  * --write-all-records
      Include passing records in the output.
  * --per-constraint
      Write one additional column per failing constraint, to show if a
      constraint passed or failed, as well as the n_failures
      total column for each row. This is set by default.
  * --no-per-constraint
      Disable the --per-constraint flag, so that the only constraint-based
      column written out is the nfailures field.
  * --original-fields
      Do not write out any of the original columns. By default, all of the
      original columns are written out, unless you use --output-fields.
  * --no-original-fields
      Do not write out any of the original columns. By default, all of the
      original columns are written out, unless you use --output-fields.
  * --output-fields FIELD1 FIELD2 ...
      Specify original columns to write out.
  * --interleave
      In the output, place the verification fields immediately after
      the original field to which they correspond.
  * --no-interleave
      In the output, place all the verification fields
      at the end the original fields
  * -r --report FORMAT1 FORMAT2 ...
      Write reports in the formats listed. Allowed formats
      are: html, text, txt, json, yaml, toml, mmarkdown, and md.
  * --index
      Include a row-number index in the output file.
      The row number is automatically included if no output fields are
      specified. Rows are usually numbered from 1, unless the
      input file already has an index.'''
      + VERIFY_FIELDS_HELP
      + help_defaults(epsilon=True)
)


def discover_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda discover',
                                     epilog=usage + DISCOVER_HELP,
                                     formatter_class=formatter)
    add_defaults(parser)
    parser.add_argument('-x', '--rex', action='store_true',
                        help='include regular expression generation')
    parser.add_argument('-X', '--no-rex', action='store_true',
                        help='exclude regular expression generation')
    parser.add_argument('-g', '--group-rex', action='store_true',
                        help='group regular expression generation')
    parser.add_argument('-G', '--no-group-rex', action='store_true',
                        help='do not group regular expression generation')
    parser.add_argument('-r', '--report', nargs='*',
                        help='Report formats to write.')
    parser.add_argument('-o', '--report-path', action='store',
                        help='Path for reports')
    add_pandas_flags(parser)
    return parser


def discover_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print(parser.epilog, file=sys.stderr)
        sys.exit(1)
    params['inc_rex'] = flags.rex or flags.group_rex or flags.no_group_rex
    params['group_rexes'] = not flags.no_group_rex
    if flags.report is not None:
        params['report_formats'] = flags.report
    else:
        params['report_formats'] = []
    if flags.report_path:
        params['report_path'] = flags.report_path

    params['engine'], params['backend'] = process_pandas_flags(flags)

    return flags


def verify_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda verify',
                                     epilog=usage + VERIFY_HELP,
                                     formatter_class=formatter)
    add_defaults(parser, epsilon=True)
    parser.add_argument('-a', '--all', action='store_true',
                        help='report all fields, even if there are '
                             'no failures')
    parser.add_argument('-f', '--fields', action='store_true',
                        help='report only fields with failures')
    parser.add_argument('-r', '--report', nargs='*',
                        help='Report formats to write.')
    parser.add_argument('-t', '--type_checking', choices=['strict', 'sloppy'],
                        help='"sloppy" means consider all numeric types '
                             'equivalent')
    add_verify_fields_flags(parser)
    return parser


def detect_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda detect',
                                     epilog=usage + DETECT_HELP,
                                     formatter_class=formatter)
    add_defaults(parser, epsilon=True)
    parser.add_argument('-o', '--report-path', action='store',
                        help='Path for reports')
    parser.add_argument('-a', '--all', action='store_true',
                        help='report all fields, even if there are '
                             'no failures')
    parser.add_argument('-f', '--fields', action='store_true',
                        help='report only fields with failures')
    parser.add_argument('-t', '--type_checking', choices=['strict', 'sloppy'],
                        help='"sloppy" means consider all numeric types '
                             'equivalent')
    parser.add_argument('--write-all-records', action='store_true',
                        help='Include passing records')
    parser.add_argument('--per-constraint', action='store_true',
                        help='Write one flag column per failing constraint '
                             'in addition to n_failures. Set by default.')
    parser.add_argument('--no-per-constraint', action='store_true',
                        help='Do not write out any per-constraint flag columns')
    parser.add_argument('--no-original-fields', action='store_true',
                        help='Do not write out original fields columns')
    parser.add_argument('--original-fields', action='store_true',
                        help='Write out original fields columns (default)')
    parser.add_argument('--no-output-fields', action='store_true',
                        help='Do not write out any original fields in the '
                             'output. By default, all original columns will '
                             'be included.')
    parser.add_argument('--output-fields', nargs='*',
                        help='Specify original columns to write out.')
    parser.add_argument('-r', '--report', nargs='*',
                        help='Report formats to write.')
    parser.add_argument('--interleave', action='store_true',
                        help='Interleave ok columns with original fields.')
    parser.add_argument('--no-interleave', action='store_true',
                        help='Do not interleave ok columns with original fields.')
    parser.add_argument('--index', action='store_true',
                        help='Include a row-number index in the output file '
                             'when detecting. Rows are usually numbered from '
                             '1, unless the input file already has an index.')
    parser.add_argument('--int', dest='int_bools', action='store_true',
                        help='Write out boolean fields as integers, with '
                             '1 for true and 0 for false.')

    parser.add_argument('--key', nargs='*',
                        help='Key or key fields to use when reporting failures')
    add_verify_fields_flags(parser)
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
    add_flags(flags, params, epsilon=True)
    va = nva = vr = nvr = False
    if flags.all:
        params['report'] = 'all'
    elif flags.fields:
        params['report'] = 'fields'
    if flags.type_checking is not None:
        params['type_checking'] = flags.type_checking
    if flags.verify_allowed_fields or flags.varf:
        params['verify_allowed_fields'] = True
        va = True
    if flags.no_verify_allowed_fields or flags.no_varf:
        params['verify_allowed_fields'] = False
        nva = True
    if flags.verify_required_fields or flags.varf:
        params['verify_required_fields'] = True
        vr = True
    if flags.no_verify_required_fields or flags.no_varf:
        params['verify_required_fields'] = False
        nvr = True

    if (va and nva):
        error('Inconsistent settings for verify-allowed-fields')
    if (vr and nvr):
        error('Inconsistent settings for verify-required-fields')

    params['engine'], params['backend'] = process_pandas_flags(flags)

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
    add_flags(flags, params, epsilon=True)
    if flags.per_constraint and flags.no_per_constraint:
        print('You must not specify both --per-constraint and '
              '--no-per-constraint.', file=sys.stderr)
        sys.exit(1)
    if flags.output_fields and flags.no_output_fields:
        print('You must not specify both --output-fields and '
              '--no-output-fields.', file=sys.stderr)
        sys.exit(1)
    if flags.type_checking is not None:
        params['type_checking'] = flags.type_checking
    if flags.write_all_records:
        params['write_all_records'] = True
    if not flags.no_per_constraint:
        params['per_constraint'] = True
    if flags.index:
        params['index'] = True
    if flags.int_bools:
        params['int_bools'] = True

    if flags.output_fields is not None:
        params['output_fields'] = flags.output_fields
    elif not flags.no_output_fields:
        params['output_fields'] = []

    if flags.report_path:
        params['report_path'] = flags.report_path

    if flags.interleave:
        params['interleave'] = True
    elif flags.no_interleave:
        params['interleave'] = False

    if flags.key:
        params['key'] = flags.key
    params['in_place'] = False  # Only applicable in API case

    # Notice the confusing similarity of these parameters,
    # params['report'] = 'records'  # already done above
    if flags.report is not None:
        params['report_formats'] = flags.report
    else:
        params['report_formats'] = []

    params['engine'], params['backend'] = process_pandas_flags(flags)

    return flags


def add_defaults(parser, help=True, seven=True, colour=True, config=True,
                 epsilon=False):
    if help:
        parser.add_argument('-?', '--?', action='help',
                            help='same as -h or --help')
    if seven:
        parser.add_argument('-7', '--ascii', action='store_true',
                            help='report without using special characters')
    if config:
        parser.add_argument('--no-config', action='store_true',
                            help='Skip loading ~/.tdda.toml')
    if colour:
        parser.add_argument('--colour', action='store_true',
                            help='Use colour in terminal output')
        parser.add_argument('--no-colour', action='store_true',
                            help='Do not not use colour in terminal output')
    if epsilon:
        parser.add_argument('-epsilon', '--epsilon', type=float,
                            help='epsilon fuzziness')


def add_flags(flags, params, epsilon=False):
    if flags.ascii:
        params['ascii'] = True

    if flags.no_colour:
        params['colour'] = False
    elif flags.colour:
        params['colour'] = True
    else:
        params['colour'] = None

    if flags.no_config:
        params['no_config'] = True
        # os.environ['TDDA_NO_CONFIG'] = '1'
        set_load(False)
    if epsilon:
        if flags.epsilon is not None:
            params['epsilon'] = float(flags.epsilon)


def add_verify_fields_flags(parser):

    parser.add_argument('--verify-required-fields', '--vrf',
                        action='store_true',
                        help='Force verify of required fields')
    parser.add_argument('--verify-allowed-fields', '--vaf',
                        action='store_true',
                        help='Force verify of allowed fields')
    parser.add_argument('--no-verify-required-fields', '--no-vrf',
                        action='store_true',
                        help='Force no verication of required fields')
    parser.add_argument('--no-verify-allowed-fields', '--no-vaf',
                        action='store_true',
                        help='Force no verification of allowed fields')
    parser.add_argument('--varf', '--vraf', action='store_true',
       help='Force verification of allowed and required fields'
    )
    parser.add_argument('--no-varf', '--no-vraf', action='store_true',
       help='Force no verification of allowed and required fields'
    )

    add_pandas_flags(parser)
