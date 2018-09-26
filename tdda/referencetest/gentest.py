# -*- coding: utf-8 -*-

"""
gentest.py: Automatic test generation for test-driven data analysis
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


import argparse
import glob
import os
import shutil
import sys
import subprocess
import tempfile
import timeit

is_python3 = sys.version_info.major >= 3
actual_input = input if is_python3 else raw_input

from tdda.referencetest.gentest_boilerplate import HEADER, TAIL

from tdda.referencetest.diffrex import find_diff_lines
from tdda.rexpy import extract

USAGE = '''python gentest.py 'quoted shell command' [test_outputfile.py] [reference files]

You can use STDOUT and STDERR (in any case) to those streams, which will
by default not be checked.
'''

MAX_SNAPSHOT_FILES = 10000

GENTEST_HELP = '''
'''


class TestGenerator:
    def __init__(self, cwd, command, script, reference_files,
                 check_stdout, check_stderr=True, require_zero_exit_code=True,
                 max_snapshot_files=MAX_SNAPSHOT_FILES,
                 relative_paths=False, with_time_log=True, iterations=2):
        self.cwd = cwd
        self.command = command
        self.raw_script = script  # as specified by user
        self.script = force_start(canonicalize(script, '.py'), 'test', 'test_')

        self.raw_files = [f for f in reference_files
                          if f.lower() not in ('stdout', 'stderr',
                                               'nonzeroexit')]
        reference_files = set(canonicalize(f) for f in self.raw_files)
        self.reference_files = {}
        for run in range(1, iterations + 1):
            self.reference_files[run] = reference_files.copy()

        self.check_stdout = check_stdout
        self.check_stderr = check_stderr
        self.require_zero_exit_code = require_zero_exit_code
        self.max_snapshot_files = max_snapshot_files
        self.relative_paths = relative_paths
        self.with_timelog = with_time_log
        self.iterations = iterations

        self.refdir = os.path.join(self.cwd, 'ref', self.name())
        self.ref_map = {}  # mapping for conflicting reference files
        self.snapshot = {}   # holds timestamps of file in ref dirs

        self.test_names = set()
        self.test_qualifier = 1

        self.create_or_empty_ref_dir()
        self.snapshot_filesystem()

        self.run_command()
        self.generate_exclusions()

        self.write_script()
        print(self.summary())


    def run_command(self):
        self.results = {}
        N = self.iterations
        for run in range(1, N + 1):
            iteration = (' (run %d of %d)' % (run, N)) if N > 1 else ''
            print('\nRunning command %s to generate output%s.\n'
                  % (repr(self.command), iteration))
            r = ExecuteCommand(self.command, self.cwd)
            self.results[run] = r

            self.fail_if_exception(r.exc)
            self.fail_if_bad_exit_code(r.exit_code)

            self.update_reference_files(run)
            self.sort_reference_files(run)
            self.copy_reference_stream_output(run)
            self.copy_reference_files(run)

    def generate_exclusions(self):
        self.exclusions = {}
        N = self.iterations
        if N < 2:
            self.exclusions = 0
        ref_files = os.listdir(self.refdir)
        for name in ref_files:
            common = []
            removals = []
            for run in range(2, N + 1):
                first = self.ref_path(name)
                later = self.ref_path(name, run)
                if os.path.isdir(first):
                    continue
                if not os.path.exists(later):
                    print('%s does not exist' % later)
                    continue
                pairs = find_diff_lines(first, later)
                for p in pairs:
                    if p.left_line_num and p.right_line_num:  # present in both
                        common.append(p.left_content)
                        common.append(p.right_content)
                    elif p[0]:  # left only
                        removals.append(p.left_content)
                    elif p[1]:  # right only
                        removals.append(p.right_content)
#            self.exclusions[name] = (extract(common), extract(removals))
            self.exclusions[name] = (extract(common), removals)

    def snapshot_fail(self):
        """
        Report failure when there are too many files to snapshot
        """
        if len(self.snapshot) > self.max_snapshot_files:
            print('*** Too many files in reference directories (max %d).'
                  % len(self.snapshot), file=sys.stderr)
            print('\nEquivalent command:\n\n  %s\n'
                  % self.cli_command(), file=sys.stderr)

            sys.exit(1)

    def fail_if_exception(self, exc):
        if exc:
            print('***ERROR: Exception occurred running command.\n%s.'
                  % str(exc), sys.stderr)
            sys.exit(1)

    def fail_if_bad_exit_code(self, exit_code):
        if exit_code != 0 and self.require_zero_exit_code:
            print('*** Non-zero exit code of %d generated by command.'
                  % exit_code, file=sys.stderr)
            print('\nTo allow non-zero exit code, use:\n\n  %s\n'
                  % self.cli_command(zec=False), file=sys.stderr)
            print('*** Test script not generated.', file=sys.stderr)
            sys.exit(1)

    def sort_reference_files(self, run):
        self.reference_files[run] = list(sorted(self.reference_files[run]))

    def copy_reference_stream_output(self, run):
        """
        Copy stdin and stdout if required
        """
        r = self.results[run]
        stdout_output = r.out
        stderr_output = r.err
        if self.check_stdout:
            self.write_expected_output(stdout_output, self.stdout_path(run))
            print('Saved (%sempty) output to stdout to %s.\n'
                  % (('non-' if stdout_output else ''),
                     self.abs_or_rel(self.stdout_path(run))))

        if self.check_stderr:
            self.write_expected_output(stderr_output, self.stderr_path(run))
            print('Saved (%sempty) output to stderr to %s.\n'
                  % (('non-' if stderr_output else ''),
                     self.abs_or_rel(self.stderr_path(run))))

    def create_or_empty_ref_dir(self):
        """
        Creates the reference directory, if it doesn't already exist.
        Empties it if it does.

        Also removes existing test script.
        """
        if os.path.exists(self.refdir):
            paths = [os.path.join(self.refdir, f)
                     for f in os.listdir(self.refdir)]
            for path in paths:
                if not os.path.isdir(path):
                    os.unlink(path)
        else:
            os.makedirs(self.refdir)

        # Create subdirs 2, 3, ..., N if there are to be N iterations
        if self.iterations > 1:
            for run in range(2, self.iterations + 1):
                d = os.path.join(self.refdir, str(run))
                if not os.path.exists(d):
                    os.mkdir(d)

        if os.path.exists(self.script):
            os.unlink(self.script)

    def snapshot_filesystem(self):
        """
        Copy timestamp on all files in nominated directories among
        reference files.
        """
        dirs = [d for d in self.reference_files[1]
                if os.path.isdir(d) and not self.ignore(d)]
        while dirs:
            dirpath = dirs.pop()
            if os.path.isdir(dirpath) and not self.ignore(dirpath):
                files = os.listdir(dirpath)
                for name in files:
                    if not self.ignore(name):  # .pyc
                        path = os.path.join(dirpath, name)
                        if os.path.isdir(path):
                            dirs.append(path)
                        else:
                            stat = os.stat(path)
                            self.snapshot[path] = stat.st_ctime
            if len(self.snapshot) > self.max_snapshot_files:
                self.snapshot_fail()

    def update_reference_files(self, run=1):
        reference_files = self.reference_files[run]
        dirs = [d for d in reference_files if os.path.isdir(d)]
        while dirs:
            for d in dirs:
                reference_files.remove(d)
                if not self.ignore(d):
                    self.add_modified_reference_files_from_dir(d, run)
            dirs = [d for d in reference_files if os.path.isdir(d)]
        self.add_globs(run)

    def add_globs(self, run):
        extras = set()
        globbed = set()
        reference_files = self.reference_files[run]
        for path in reference_files:
            if '?' in path or '*' in path:
                globbed.add(path)
                matches = glob.glob(path)
                if not matches:
                    print("*** Warning: Pattern '%s' matched no files; "
                          "ignoring." % path)
                else:
                    extras = extras.union(set(matches))
        self.reference_files[run] = reference_files.union(extras) - globbed

    def add_modified_reference_files_from_dir(self, dirpath, run=1):
        files = os.listdir(dirpath)
        reference_files = self.reference_files[run]
        for name in files:
            if not self.ignore(name):  # .pyc
                path = os.path.join(dirpath, name)
                ctime = os.stat(path).st_ctime
                if (path not in self.snapshot
                        or ctime > self.snapshot[path]
                        or os.path.isdir(path)):
                    reference_files.add(path)

    def name(self):
        name = os.path.basename(self.script)[4:-3]  # knock off test and .py
        return name[1:] if name.startswith('_') else name

    def ignore(self, name):
        if os.path.isdir(name) and name.startswith(self.refdir):
            return True
        return (name == '__pycache__'
                or name.endswith('.pyc')
                or name == '.DSStore')

    def copy_reference_files(self, run):
        """
        Copy files specified to ref subdirectory.

        If run > 1, put in numbered subdirectory of there.
        """
        ref_paths = {os.path.abspath(self.ref_path('stdout')).lower(),
                     os.path.abspath(self.ref_path('stderr')).lower()}
        failures = False
        for path in self.reference_files[run]:
            if os.path.isdir(path):
                print('DIR:', path)
                continue
            ref_path = self.ref_path(path, run)
            suffix = 0
            while ref_path.lower() in ref_paths:
                if suffix:
                    ref_path = ref_path[:-len(str(suffix))]
                suffix += 1
                ref_path = ref_path + str(suffix)
            if suffix:
                self.ref_map[path] = ref_path
            ref_paths.add(ref_path.lower())
            try:
                shutil.copyfile(path, ref_path)
                print('Copied %s to %s' % (as_pwd_repr(path, self.cwd),
                                           as_pwd_repr(ref_path, self.cwd)))
            except:
                print('*** Failed to copy %s to %s'
                      % (as_pwd_repr(path, self.cwd),
                         as_pwd_repr(ref_path, self.cwd)))
                failures = True
        if failures:
            print('\n*** Although not all files specified were successfully '
                  'copied,\n    still generating the test.')

    def write_expected_output(self, out, path):
        """
        Write the output (stdout or stderr) actually generated by
        (the first run of) command to a file for reference testing.
        """
        with open(path, 'w') as f:
            f.write(out)

    def stdout_path(self, run=1):
        """
        Path to write stdout to, if it is being checked.
        """
        return self.ref_path('STDOUT', run=run)

    def stderr_path(self, run=1):
        """
        Path to write stderr to, if it is being checked.
        """
        return self.ref_path('STDERR', run=run)

    def ref_path(self, path, run=1):
        """
        Returns the location for the reference file corresponding
        to the (original) path provided.

        If run > 1, add subdir numbered by run after refdir
        (e.g. write file name to refdir/2/name, if run = 2)
        """
        if run == 1:
            return os.path.join(self.refdir, os.path.basename(path))
        else:
            return os.path.join(self.refdir, str(run), os.path.basename(path))

    def write_script(self):
        """
        Generate the test script.
        """
        r = self.results[1]
        reference_files = self.reference_files[1]
        with open(self.script, 'w') as f:
            f.write(HEADER % {
                'SCRIPT': os.path.basename(self.script),
                'GEN_COMMAND': self.cli_command(),
                'COMMAND': repr(self.command),
                'CWD': repr(self.cwd),
                'NAME': repr(self.name()),
                'EXIT_CODE': r.exit_code
            })
            if self.check_stdout:
                path = as_join_repr(self.stdout_path(), self.cwd, self.name())
                exc = self.exclusions.get('STDOUT')
                (patterns, removals) = exc if exc else (None, None)
                f.write(test_def('stdout', 'self.output', 'String', path,
                                 patterns, removals))
            if self.check_stderr:
                path = as_join_repr(self.stderr_path(), self.cwd, self.name())
                exc = self.exclusions.get('STDERR')
                (patterns, removals) = exc if exc else (None, None)
                f.write(test_def('stderr', 'self.error', 'String', path,
                                 patterns, removals))

            for path in reference_files:
                testname = self.test_name(path)
                ref_path = self.ref_map.get(path, self.ref_path(path))
                ref_path = as_join_repr(ref_path, self.cwd, self.name())
                actual_path = as_join_repr(path, self.cwd, self.name())
                exc = self.exclusions.get(path)
                (patterns, removals) = exc if exc else (None, None)
                f.write(test_def(testname, actual_path, 'File', ref_path,
                                 patterns, removals))

            f.write(TAIL)
        print('\nTest script written as %s' % self.abs_or_rel(self.script))

    def test_name(self, path):
        """
        Generates a test name corresponding to the path provided.
        """
        name = os.path.basename(path)
        testname = ''.join(c if c.isalnum() else '_' for c in name)
        if testname in self.test_names:
            self.test_qualifier += 1
            testname += str(self.test_qualifier)
        self.test_names.add(testname)
        return testname

    def cli_command(self, zec=None):
        files = ' '
        files += ' '.join(repr(f) for f in self.raw_files)
        if self.check_stdout:
            files += ' STDOUT'
        if self.check_stderr:
            files += ' STDERR'
        if zec is None:
            zec = self.require_zero_exit_code
        if not zec:
            files += ' NONZEROEXIT'
        return ('tdda gentest %s %s'
                % (repr(self.command),
                   repr(os.path.basename(self.script)))
                + (files if files.strip() else ''))

    def summary(self, inc_timings=True):
        lines = ['']
        r = self.results[1]  # first run used as base copy to write
        reference_files = self.reference_files[1]
        if inc_timings:
            lines = [
                '',
                '',
                'Command execution took: %s' % format_time(r.duration)
            ]
        lines += [
            '',
            '',
            'SUMMARY:',
            '',
            'Directory to run in:   %s' % ('.' if self.relative_paths
                                               else self.cwd),
            'Shell command:         %s' % self.command,
            'Test script generated: %s' % self.raw_script,
            'Reference files:       %s' % ('' if reference_files
                                              else '[None]'),
        ] + [
            '    %s' % as_pwd_repr(f, self.cwd) for f in reference_files

        ] + [
            'Check stdout:          %s' % stream_desc(self.check_stdout,
                                                      r.out),
            'Check stderr:          %s' % stream_desc(self.check_stderr,
                                                      r.err),
            'Expected exit code:    %d' % r.exit_code,
            '',
        ]
        return '\n'.join(lines)

    def abs_or_rel(self, path):
        """
        Convenience function for as_join_repr with as_pwd=.
        """
        return (as_join_repr(path, self.cwd, as_pwd='.') if self.relative_paths
                                                         else path)

class ExecuteCommand:
    """
    Executes command, with cwd as provided, in a subprocess.

    Sets properties:
        self.out       --- captured output to stdout
        self.err       --- captured output to sterr
        self.exit_code --- exit code from the command
        self.exc       --- any exception raised
        self.duration  --- time taken, in seconds to run the command
    """
    def __init__(self, command, cwd, timelog=None):
        t = timeit.default_timer()
        self.out = self.err = self.exc = self.exit_code = None
        try:
            sp = subprocess.Popen(command, stdin=None,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True,
                                  cwd=cwd, close_fds=True, env=os.environ)
            self.out, self.err = sp.communicate()
            self.exit_code = sp.returncode
            if is_python3:
                self.out = self.out.decode('UTF-8')
                self.err = self.err.decode('UTF-8')
        except Exception as exc:
            self.exc = exc
        self.duration = timeit.default_timer() - t


def exec_command(command, cwd):
    r = ExecuteCommand(command, cwd)
    return (r.out, r.err, r.exc, r.exit_code, r.duration)


def stream_desc(check, expected):
    L = len(expected)
    lines = len(expected.splitlines())
    was = ('empty' if L == 0
                   else repr(expected) if L < 40
                   else '%d line%s' % (lines, 's' if lines != 1 else ''))
    return '%s (was %s)' % ('yes' if check else 'no', was)


def canonicalize(path, default_ext=None, reject_other_exts=True):
    """
    Canonicalize path by:
        - handling ~ at start of path
        - expanding relative paths to full paths
        - adding default_ext if specified and the path has no extension.
          (By default, complains if you supply a default extension and
           the actual one is different.)
    """
    if default_ext is not None:
        stem, ext = os.path.splitext(path)
        if reject_other_exts and ext and ext != default_ext:
            print('\n*** Extension %s on %s must be %s' % (ext, path,
                                                           default_ext))
            sys.exit(1)
        path = stem + (ext or default_ext)
    if os.path.isabs(path):
        return path
    else:
        return os.path.abspath(os.path.expanduser(path))


def as_pwd_repr(path, cwd):
    """
    Convenience function for as_join_repr with as_pwd=$(pwd)
    """
    return as_join_repr(path, cwd, as_pwd='$(pwd)')


def as_join_repr(path, cwd, name=None, as_pwd=None):
    """
    This function aims to produce more comprehensible representations
    of paths under cwd (the assumed current working directory, as would
    be returned by $(pwd) in the shell).

    If the path given is not in cwd, the quoted string literal of the path
    is returned.

    If it is in cwd, the behaviour depends on the value of as_pwd.

    If as_pwd is True, it will be returned as

        '$(pwd)/tail'

    where tail is the path after the directory cwd.

    If as_pwd is False, the default, then we first check if the path
    point to a file in the subdirectory os.path.join(cwd, 'ref', name)
    (the location for reference files for this script).

    If it is, the path is returned as

        os.path.join(REFDIR, reftail)

    where reftail is the path provided with REFDIR knocked off the front.

    Otherwise, it is returned as

        os.path.join(CWD, tail)

    with tail being the path with cwd removed from the front.
    """
    if cwd.endswith(os.path.sep):
        cwd = cwd[:-len(os.path.sep)]
    if path.startswith(cwd + os.path.sep):
        if path not in (cwd, cwd + os.path.sep):
            tail = path[len(cwd):]
            if os.path.isabs(tail):
                tail = tail[1:]
            if as_pwd:
                return '%s/%s' % (as_pwd, tail)
            else:
                ref = os.path.join('ref', name)
                L = len(ref) + len(os.path.sep)
                if tail.startswith(ref + os.path.sep):
                    tail = tail[L:]
                    return 'os.path.join(REFDIR, %s)' % repr(tail)
                else:
                    return 'os.path.join(CWD, %s)' % repr(tail)
    return repr(path)


def test_def(name, actual, kind, ref_file_path, patterns, removals):
    lines = ['', 'def test_%s(self):' % name]
    extras = []
    assert kind in ('File', 'String')
    assert_fn = 'self.assert%sCorrect' % kind
    spc = ' ' * (len(assert_fn) + 5)
    if patterns:
        lines.append('    patterns = [')
        for p in patterns:
            lines.append('        %s,' % quote_raw(p))
        lines.append('    ]')
        extras.append(spc + 'ignore_patterns=patterns')
    if removals:
        lines.append('    removals = [')
        for p in removals:
            lines.append('        %s,' % repr(p))
        lines.append('    ]')
        rspc = '' if extras else spc
        extras.append(rspc + 'remove_lines=removals')
    ref_file_line = spc + ref_file_path + (',' if extras else ')')
    lines.extend(['    %s(%s,' % (assert_fn, actual), ref_file_line])
    if extras:
        joint = ',\n' + spc + (' ' * 4)
        lines.append(joint.join(extras) + ')')
    return '\n    '.join(lines) + '\n'


def quote_raw(s):
    """
    Attempt to return a representation of s as a raw string,
    falling back to repr if that's just too damn hard.
    """
    if "'" not in s:
        return "r'%s'" % s
    elif '"' not in s:
        return 'r"%s"' % s
    elif "'''" not in s:
        return "r'''%s'''" % s
    elif '"""' not in s:
        return 'r"""%s"""' % s
    else:
        return repr(s)


def sanitize_string(string):
    """
    Replaces all non-alphas in string with '_'
    """
    return ''.join(c if c.isalnum() else '_' for c in string)


def force_start(path, checked_prefix, default_prefix):
    """
    Changes the filename in the path provided by adding the default_prefix
    given if the file at path does not begin with checked_prefix.

    e.g.

        force_start('/home/jacqui/1.py', 'test', 'test_')
            --> '/home/jacqui/test_1.py'
    """
    folder, name = os.path.split(path)
    if not name.startswith(checked_prefix):
        name = default_prefix + name
    return os.path.join(folder, name)


def getline(prompt='', empty_ok=True, default=None):
    """
    Get a line from the user.

    Repeatedly issues the prompt given (if any) until the stripped input
    is non-empty, unless empty_ok is set.

    In either case, returns the stripped line provided.
    """
    done = False
    while not done:
        if prompt:
            print(prompt + ((' [%s]:' % default) if default else ':'), end=' ')
        line = actual_input().strip()
        if line == '' and default:
            line = default
        done = empty_ok or line
    return line


def yes_no(msg, default='y'):
    check = None
    while check is None:
        reply = getline('%s?: [%s]' % (msg, default)).lower().strip()
        if reply in ('y', 'yes'):
            check = True
        elif reply in ('n', 'no'):
            check = False
        elif reply == '':
            check = default == 'y'
    return check


def format_time(duration):
    """
    Format time in seconds, with at least two significant figures
    """
    dps = 2
    while dps < 10 and duration < pow(10, -dps + 1):
        dps += 1
    return ('%%.%dfs' % dps) % duration


def wizard():
    """
    Gather test specification from users with Q-and-A interface
    """
    shellcommand = getline('Enter shell command to be tested', empty_ok=False)
    output_script = getline('Enter name for test script', empty_ok=False,
                            default='test_' + sanitize_string(shellcommand))
    reference_files = []
    check_cwd = yes_no('Check all files written under $(pwd)')
    if check_cwd:
        reference_files.append('.')
    print('Enter other files to be checked, one per line, then blank line:')
    ref = getline()
    while ref:
        reference_files.append(ref)
        ref = getline()
    check_stdout = yes_no('Check stdout')
    check_stderr = yes_no('Check stderr')
    require_zero_exit_code = yes_no('Exit code should be zero')
    return (shellcommand, output_script, reference_files,
            check_stdout, check_stderr, require_zero_exit_code)


def gentest_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda gentest',
                                     epilog=usage + GENTEST_HELP,
                                     formatter_class=formatter)
    parser.add_argument('-?', '--?', action='help',
                        help='same as -h or --help')
    parser.add_argument('-m', '--max-files', type=int,
                        help='max files to track')
    parser.add_argument('-r', '--relative-paths', action='store_true',
                        help='show relative paths wherever possible')
    return parser


def gentest_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if flags.max_files:
        params['max_files'] = flags.max_files
    if flags.relative_paths:
        params['relative_paths'] = True
    return flags, more


def gentest_params(args):
    parser = gentest_parser()
    kw = {}
    _, positional_args = gentest_flags(parser, args, kw)
    return positional_args, kw


def gentest_wrapper(args):
    positional_args, kw = gentest_params(args)
    reference_files = positional_args[2:]
    command = positional_args[0] if positional_args else None
    script = positional_args[1] if len(positional_args) > 2 else None
    gentest(command, script, reference_files, **kw)


def gentest(shellcommand, output_script, reference_files,
            max_snapshot_files=MAX_SNAPSHOT_FILES, relative_paths=False):
    """
    Generate code python in output_script for running the
    shell command given and checking the reference files
    provided.

    If no reference files are provided, check stdout.

    By default, always check stderr.
    """
    if shellcommand is None and output_script is None:
        (shellcommand,
         output_script,
         reference_files,
         check_stdout,
         check_stderr,
         require_zero_exit_code) = wizard()
    else:
        check_stdout = False
        check_stderr = False
        require_zero_exit_code = True
    cwd = os.getcwd()
    if shellcommand is None:
        print('\n*** USAGE:\n  %s' % USAGE, file=sys.stderr)
        sys.exit(1)
    if not output_script:
        output_script = 'test_' + sanitize_string(shellcommand)
    lcrefs = [f.lower() for f in reference_files]
    if 'stdout' in lcrefs:
        check_stdout = True
    if 'stderr' in lcrefs:
        check_stderr = True
    if 'nonzeroexit' in lcrefs:
        require_zero_exit_code = False
    if not (set(lcrefs) - set(['stdout', 'stderr', 'nonzeroexit'])):
        reference_files = reference_files + ['.',]
    TestGenerator(cwd, shellcommand, output_script, reference_files,
                  check_stdout, check_stderr, require_zero_exit_code,
                  max_snapshot_files=max_snapshot_files,
                  relative_paths=relative_paths)


if __name__ == '__main__':
    gentest_wrapper(sys.argv[1:])

