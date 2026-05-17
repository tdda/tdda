# -*- coding: utf-8 -*-

"""
Helpers for command-line option flags for discover and verify
"""

import argparse
import os
import sys

from tdda.man.utils import get_help, print_help
from tdda.state import set_load
from tdda.utils import error
from tdda.commonflags import add_pandas_flags, process_pandas_flags


class ManPageParser(argparse.ArgumentParser):
    """ArgumentParser that shows the man page for --help instead of argparse output."""
    def __init__(self, cmd, *args, **kwargs):
        self._man_cmd = cmd
        super().__init__(*args, **kwargs)

    def print_help(self, file=None):
        print_help(self._man_cmd, file or sys.stdout)

    def print_usage(self, file=None):
        f = file or sys.stderr
        print(f'usage: {self.prog} [options] ...', file=f)
        print(f'Try "{self.prog} --help" for more information.', file=f)


def help_defaults(
    help=True, seven=True, colour=True, config=True, epsilon=False
):
    out = []
    if epsilon:
        out.append("""
  * --epsilon E
      Use this value of epsilon for fuzziness in comparing numeric values.
""")
    if seven:
        out.append("""
  * -7, --ascii
      Report in ASCII form, without using special characters.
""")
    if colour:
        out.append("""
  * --colour
      Coloured output
  * --no-colour
      Monochrome output
""")
    if config:
        out.append("""
  * -N, --no-config
      Do not configure using ~/tdda.toml: use all defaults
""")
    return ''.join(o.rstrip() for o in out) + '\n'

    if help:
        out.append("""
  * -?, --help
      Show help
""")
    return ''.join(o.rstrip() for o in out) + '\n'


def discover_parser(usage=''):
    parser = ManPageParser(
        'discover',
        prog='tdda discover',
    )
    add_defaults(parser)
    parser.add_argument(
        '-x',
        '--rex',
        action='store_true',
        help='include regular expression generation',
    )
    parser.add_argument(
        '-X',
        '--no-rex',
        action='store_true',
        help='exclude regular expression generation',
    )
    parser.add_argument(
        '-g',
        '--group-rex',
        action='store_true',
        help='group regular expression generation',
    )
    parser.add_argument(
        '-G',
        '--no-group-rex',
        action='store_true',
        help='do not group regular expression generation',
    )
    parser.add_argument(
        '-r', '--report', nargs='*', help='Report formats to write.'
    )
    parser.add_argument(
        '-o', '--report-path', action='store', help='Path for reports'
    )
    parser.add_argument(
        '--no-md', action='store_true', help='Do not create metadata'
    )
    parser.add_argument(
        '--no-allowed-required--no-ar',
        action='store_true',
        help='Do not create allowed and required field constraints',
    )
    parser.add_argument(
        '--allowed',
        action='store_true',
        help='Create allowed fields dataset constraint',
    )
    parser.add_argument(
        '--no-allowed',
        action='store_true',
        help='Do not create allowed fields dataset constraint',
    )
    parser.add_argument(
        '--required',
        action='store_true',
        help='Create required fields dataset constraint',
    )
    parser.add_argument(
        '--no-required',
        action='store_true',
        help='Do not create required fields dataset constraint',
    )
    parser.add_argument(
        '--ar',
        action='store_true',
        help='Create allowed and required fields dataset constraints',
    )
    parser.add_argument(
        '--no-ar',
        action='store_true',
        help='Do not create allowed or required fields dataset constraints',
    )
    add_pandas_flags(parser)
    return parser


def discover_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        parser.print_help(sys.stderr)
        sys.exit(1)
    params['inc_rex'] = flags.rex or flags.group_rex or flags.no_group_rex
    params['group_rexes'] = not flags.no_group_rex
    if flags.report is not None:
        params['report_formats'] = flags.report
    else:
        params['report_formats'] = []
    if flags.report_path:
        params['report_path'] = flags.report_path
    if flags.no_md:
        params['no_md'] = flags.no_md

    params['engine'], params['backend'] = process_pandas_flags(None, flags)

    params['allowed_fields'] = not (flags.no_allowed or flags.no_ar)
    params['required_fields'] = not (flags.no_required or flags.no_ar)

    return flags


def verify_parser(usage=''):
    parser = ManPageParser(
        'verify',
        prog='tdda verify',
    )
    add_defaults(parser, epsilon=True)
    parser.add_argument(
        '-a',
        '--all',
        action='store_true',
        help='report all fields, even if there are no failures',
    )
    parser.add_argument(
        '-f',
        '--fields',
        action='store_true',
        help='report only fields with failures',
    )
    parser.add_argument(
        '-r', '--report', nargs='*', help='Report formats to write.'
    )
    parser.add_argument(
        '-t',
        '--type_checking',
        choices=['strict', 'sloppy', 'loose'],
        help='"loose" (or "sloppy") means consider all numeric types equivalent',
    )
    add_verify_fields_flags(parser)
    return parser


def detect_parser(usage=''):
    parser = ManPageParser(
        'detect',
        prog='tdda detect',
    )
    add_defaults(parser, epsilon=True)
    parser.add_argument(
        '-o', '--report-path', action='store', help='Path for reports'
    )
    parser.add_argument(
        '-a',
        '--all',
        action='store_true',
        help='report all fields, even if there are no failures',
    )
    parser.add_argument(
        '-f',
        '--fields',
        action='store_true',
        help='report only fields with failures',
    )
    parser.add_argument(
        '-t',
        '--type_checking',
        choices=['strict', 'sloppy', 'loose'],
        help='"loose" (or "sloppy") means consider all numeric types equivalent',
    )
    parser.add_argument(
        '--write-all-records',
        action='store_true',
        help='Include passing records',
    )
    parser.add_argument(
        '--per-constraint',
        action='store_true',
        help='Write one flag column per failing constraint '
        'in addition to n_failures. Set by default.',
    )
    parser.add_argument(
        '--no-per-constraint',
        action='store_true',
        help='Do not write out any per-constraint flag columns',
    )
    parser.add_argument(
        '--no-original-fields',
        action='store_true',
        help='Do not write out original fields columns',
    )
    parser.add_argument(
        '--original-fields',
        action='store_true',
        help='Write out original fields columns (default)',
    )
    parser.add_argument(
        '--no-output-fields',
        action='store_true',
        help='Do not write out any original fields in the '
        'output. By default, all original columns will '
        'be included.',
    )
    parser.add_argument(
        '--output-fields',
        nargs='*',
        help='Specify original columns to write out.',
    )
    parser.add_argument(
        '-r', '--report', nargs='*', help='Report formats to write.'
    )
    parser.add_argument(
        '--interleave',
        action='store_true',
        help='Interleave ok columns with original fields.',
    )
    parser.add_argument(
        '--no-interleave',
        action='store_true',
        help='Do not interleave ok columns with original fields.',
    )
    parser.add_argument(
        '--index',
        action='store_true',
        help='Include a row-number index in the output file '
        'when detecting. Rows are usually numbered from '
        '1, unless the input file already has an index.',
    )
    parser.add_argument(
        '--int',
        dest='int_bools',
        action='store_true',
        help='Write out boolean fields as integers, with 1 for true and 0 for false.',
    )

    parser.add_argument(
        '--key',
        nargs='*',
        help='Key or key fields to use when reporting failures',
    )
    add_verify_fields_flags(parser)
    return parser


def verify_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        print('Unexpected arguments %s\n' % ' '.join(more), file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)
    params.update(
        {
            'report': 'all',
            'ascii': False,
        }
    )
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

    if va and nva:
        error('Inconsistent settings for verify-allowed-fields')
    if vr and nvr:
        error('Inconsistent settings for verify-required-fields')

    params['engine'], params['backend'] = process_pandas_flags(None, flags)

    return flags


def detect_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if len(more) > 0:
        parser.print_help(sys.stderr)
        sys.exit(1)
    params.update(
        {
            'report': 'records',
            'ascii': False,
        }
    )
    add_flags(flags, params, epsilon=True)
    if flags.per_constraint and flags.no_per_constraint:
        print(
            'You must not specify both --per-constraint and --no-per-constraint.',
            file=sys.stderr,
        )
        sys.exit(1)
    if flags.output_fields and flags.no_output_fields:
        print(
            'You must not specify both --output-fields and --no-output-fields.',
            file=sys.stderr,
        )
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

    params['engine'], params['backend'] = process_pandas_flags(None, flags)

    return flags


def add_defaults(
    parser, help=True, seven=True, colour=True, config=True, epsilon=False
):
    if help:
        parser.add_argument(
            '-?', '--?', action='help', help='same as -h or --help'
        )
    if seven:
        parser.add_argument(
            '-7',
            '--ascii',
            action='store_true',
            help='report without using special characters',
        )
    if config:
        parser.add_argument(
            '-N', '--no-config',
            action='store_true',
            help='Skip loading ~/.tdda.toml',
        )
    if colour:
        parser.add_argument(
            '--colour',
            action='store_true',
            help='Use colour in terminal output',
        )
        parser.add_argument(
            '--no-colour',
            action='store_true',
            help='Do not not use colour in terminal output',
        )
    if epsilon:
        parser.add_argument(
            '-epsilon', '--epsilon', type=float, help='epsilon fuzziness'
        )


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
    parser.add_argument(
        '--verify-required-fields',
        '--vrf',
        action='store_true',
        help='Force verify of required fields',
    )
    parser.add_argument(
        '--verify-allowed-fields',
        '--vaf',
        action='store_true',
        help='Force verify of allowed fields',
    )
    parser.add_argument(
        '--no-verify-required-fields',
        '--no-vrf',
        action='store_true',
        help='Force no verication of required fields',
    )
    parser.add_argument(
        '--no-verify-allowed-fields',
        '--no-vaf',
        action='store_true',
        help='Force no verification of allowed fields',
    )
    parser.add_argument(
        '--varf',
        '--vraf',
        action='store_true',
        help='Force verification of allowed and required fields',
    )
    parser.add_argument(
        '--no-varf',
        '--no-vraf',
        action='store_true',
        help='Force no verification of allowed and required fields',
    )

    add_pandas_flags(parser)
