# -*- coding: utf-8 -*-

"""
gentest.py: Automatic test generation for test-driven data analysis
"""

import argparse
import datetime
import getpass
import glob
import os
import re
import shutil
import socket
import sys
import subprocess
import tempfile
import timeit

from collections import OrderedDict

is_python3 = sys.version_info.major >= 3
actual_input = input if is_python3 else raw_input

from tdda.referencetest.gentest_boilerplate import HEADER, TAIL

from tdda.referencetest.diffrex import find_diff_lines
from tdda.referencetest.utils import (FileType, get_encoding,
                                      protected_readlines)
from tdda.rexpy import extract

USAGE = '''tdda gentest        (to run wizard)

or

tdda gentest 'shell command' [FLAGS] [test_output.py [reference files]]

Gentest writes tests, so you don't have to.™
'''

MAX_SNAPSHOT_FILES = 10000
MAX_SPECIFIC_DATE_VARIANTS = 5

GENTEST_HELP = USAGE

MONTH_TERM = (r'(jan|january|feb|february|mar|march|apr|april|may|jun|june|'
              r'jul|jul|aug|august|sep|sept|september|oct|october|nov|'
              r'november|dec|december)\,?\s?')
NUM_DATE_TERM = r'(\d{1,4})[/\-\.](\d{1,2})[/\-\.](\d{1,4})'
EURO_STR_DATE_TERM = r'(\d{1,2})\s' + MONTH_TERM + '(\d{2,4})'
US_STR_DATE_TERM = MONTH_TERM+ r'(\d{1,2})\,?\s?' + '(\d{2,4})'
TIME_TERM = r'(\d{1,2}):(\d{1,2})(:\d{1,2}|)(\.?\d*)'
TZ_TERM = r' ?([+\-]\d{2}:?\d{2})?\]?Z?'
TS_TERM = '[ T]'
DS = '.*'
ND = r'(|.*[^\d])'
NUM_DATETIME_RE = re.compile(ND + NUM_DATE_TERM + TS_TERM + TIME_TERM
                             + TZ_TERM + DS)
NUM_DATE_RE = re.compile(ND + NUM_DATE_TERM + DS)
EURO_STR_DATETIME_RE = re.compile(ND + EURO_STR_DATE_TERM + TS_TERM + TIME_TERM
                                  + TZ_TERM + DS)
EURO_STR_DATE_RE = re.compile(ND + EURO_STR_DATE_TERM + DS)
US_STR_DATETIME_RE = re.compile(ND + US_STR_DATE_TERM + TS_TERM + TIME_TERM
                                + TZ_TERM + DS)
US_STR_DATE_RE = re.compile(ND + US_STR_DATE_TERM + DS)

D2 = re.compile(r'^.*\d{2}.*$')

MONTH_MAP = {
    'jan': 1,
    'feb': 2,
    'mar': 3,
    'apr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'sep': 9,
    'oct': 10,
    'nov': 11,
    'dec': 12,
}

TMPDIR = tempfile.mkdtemp()        # Writable area for tests
TERM_TMPDIR = TMPDIR + os.path.sep
DEFAULT_TMP_DIR_SHELL_VAR = 'TMPDIR'


class Specifics:
    """
    Container for over-specific items found in output lines.
    """
    __slots__ = ['line', 'host', 'ip', 'cwd', 'homedir', 'tmpdir',
                 'user', 'datelike', 'dtlike',
                 'rex_inputs', 'remove', 'substring']

    def __init__(self, line, host=False, ip=False, cwd=False, homedir=False,
                 tmpdir=False, user=False, datelike=False, dtlike=False,
                 rex_inputs=None, remove=None, substring=None):
        self.line = line
        self.host = host
        self.ip = ip
        self.cwd = cwd
        self.homedir = homedir
        self.tmpdir = tmpdir
        self.user = user
        self.datelike = datelike
        self.dtlike = dtlike
        self.rex_inputs = rex_inputs  # strings to be given to rexpy
        self.remove = remove
        self.substring = substring  # substring

    def __repr__(self):
        return ('Specifics(%s)'
                % (',\n              '.join('%s=%s'
                                            % (k, repr(getattr(self, k)))))
                   for k in __slots__)


class TestGenerator:
    def __init__(self, cwd, command, script, reference_files,
                 check_stdout, check_stderr=True, require_zero_exit_code=True,
                 no_clobber=False, max_snapshot_files=MAX_SNAPSHOT_FILES,
                 relative_paths=False, with_time_log=True, iterations=2,
                 tmp_dir_shell_var=DEFAULT_TMP_DIR_SHELL_VAR, verbose=True):
        self.cwd = cwd
        self.tmp_dir_shell_var = tmp_dir_shell_var  # If None, not used
        self.tmpdir = TMPDIR
        if tmp_dir_shell_var:
            os.environ[tmp_dir_shell_var] = TMPDIR
            reference_files.append(TMPDIR)
        self.tmpdir_used = False  # Updated later if used
        self.command = command
        self.raw_script = script  # as specified by user
        self.script = force_start(canonicalize(script, '.py'), 'test', 'test_')

        self.raw_files = reference_files.copy()
        self.verbose = verbose
        reference_files = set(canonicalize(f) for f in self.raw_files)
        self.reference_files = {}
        for run in range(1, iterations + 1):
            self.reference_files[run] = reference_files.copy()

        self.check_stdout = check_stdout
        self.check_stderr = check_stderr
        self.no_clobber = no_clobber
        self.require_zero_exit_code = require_zero_exit_code
        self.max_snapshot_files = max_snapshot_files
        self.relative_paths = relative_paths
        self.with_timelog = with_time_log
        self.iterations = iterations
        self.warnings = []

        self.host = socket.gethostname()
        try:
            self.ip_address = socket.gethostbyname(self.host)
        except:  # 
            self.ip_address = None
        self.homedir = home_dir()
        self.user = getpass.getuser()
        self.user_in_home = self.user in self.homedir
        self.cwd_in_home = self.cwd.startswith(self.homedir)

        self.refdir = os.path.join(self.cwd, 'ref', self.ref_subdir())
        self.ref_map = {}    # mapping for conflicting reference files
        self.snapshot = {}   # holds timestamps of file in ref dirs

        self.test_names = set()
        self.test_qualifier = 1

        if self.no_clobber:
            self.check_for_clobbering()

        if iterations > 0:
            self.create_or_empty_ref_dir()
            self.snapshot_filesystem()

            self.run_command()
            self.generate_exclusions()

            self.write_script()
            if self.verbose:
                print(self.summary())
        self.remove_extra_reference_files()

    def check_for_clobbering(self):
        rest = 'No-clobber is set.\nRemove or run without --no-clobber (-C).'
        if os.path.exists(self.script):
            if os.path.exists(self.refdir):
                self.fail('Target test script %s\n'
                          'and reference directory %s exist.\n%s'
                          % (self.script, self.refdir, rest))
            else:
                self.fail('Target test script %s exist.\n%s'
                          % (self.script, rest))
        elif os.path.exists(self.refdir):
            self.fail('Reference directory %s exists.\n%s'
                      % (self.refdir, rest))

    def run_command(self):
        self.results = {}
        N = self.iterations
        for run in range(1, N + 1):
            iteration = (' (run %d of %d)' % (run, N)) if N > 1 else ''
            if self.verbose:
                print('\nRunning command %s to generate output%s.'
                      % (repr(self.command), iteration))
            if run == 1:
                self.start_time = datetime.datetime.now()
            r = ExecuteCommand(self.command, self.cwd)
            if run == 1:
                self.stop_time = datetime.datetime.now()
            self.results[run] = r

            self.fail_if_exception(r.exc)
            self.fail_if_bad_exit_code(r)

            self.update_reference_files(run)
            self.sort_reference_files(run)
            self.copy_reference_stream_output(run)
            self.copy_reference_files(run)
        self.set_min_max_time()

    def set_min_max_time(self):
        """
        To allow for timezone differences etc. (you might be running
        on a machine at GMT+11 but writing at GMT-11) we really
        have to allow 24 hours before the start time and 24 hours
        after the stop time to be (fairly) safe.
        """
        m = self.start_time + datetime.timedelta(days=-1)
        self.min_time = datetime.datetime(m.year, m.month, m.day)
        M = self.stop_time + datetime.timedelta(days=1)
        self.max_time = datetime.datetime(M.year, M.month, M.day)

    def generate_exclusions(self):
        """
        Generate exclusion patterns needed for each file,
        based on analysing differences between the two runs
        and searching for strings that look to be over-specific
        to the machine/time etc. that the command was run.

        Sets self.filetypes and self.exclusions
        """
        self.exclusions = {}
        self.filetypes = {}
        if self.iterations < 2:  # though could still do specifics...
            return
        ref_files = [r for r in os.listdir(self.refdir)
                       if not os.path.isdir(self.ref_path(r))]
        for name in ref_files:
            filetype, exc = self.generate_exclusions_for_file(name)
            self.filetypes[name] = filetype
            if exc is not None:
                self.update_exclusions_with_specifics(name, exc)

    def generate_exclusions_for_file(self, name):
        """
        Generate exclusion patterns needed for the specific named
        (reference) file.
        This is based on two things:
          1. analysing differences between the output from the two
             (or more) runs
          2. searching for strings that look to be over-specific
             to the machine/time etc. that the command was run.
        Files passed in should not be directories.

        Exclusions are return as 3-tuples in self.exclusions, keyed
        on name.

        Return value is (filetype, exclusions)
        """
        common = []       # similar but different content from both sides
        removals = []     # lines to be removed (present only on one side)

        first = self.ref_path(name)
        filetype = FileType(first)
        lines = protected_readlines(first, filetype)
        if lines is None:
            return filetype, None
        specifics = self.check_for_specific_references(first, filetype)

        for run in range(2, self.iterations + 1):
            later = self.ref_path(name, run)
            if not os.path.exists(later):
                if self.verbose:
                    print('%s does not exist' % later)
                continue
            pairs = find_diff_lines(first, later, filetype)
            for p in pairs:
                if p.left_line_num and p.right_line_num:  # present in both
                    common.append(p.left_content)
                    common.append(p.right_content)
                elif p.left_line_num:     # left only
                    removals.append(p.left_content)
                elif p.right_line_num:    # right only
                    removals.append(p.right_content)
                self.update_specifics(specifics, p)
        return filetype, (specifics, common, removals)

    def update_specifics(self, specifics, p):
        """
        The potentially over-specific lines are identified before
        differences between the files are generated.

        The properties rex_inputs, remove and substring, on specifics,
        are all set to None in the object passed in.

        This method updates those values for any specific patterns that
        only occur in lines identified as having differences.
        """
        nL = p.left_line_num
        if not nL:
            return

        rex_inputs = remove = substring = None
        if p.right_line_num:
            rex_inputs = (p.left_content, p.right_content)
        else:
            remove = p.left_content

        if nL not in specifics:  # add Specifics for line with diffs only
            specifics[nL] = Specifics(p.left_content)

        s = specifics[nL]
        s.rex_inputs = rex_inputs
        s.remove = remove
        s.substring = substring

    def update_exclusions_with_specifics(self, name, exc, debug=False):
        """
        The rex_inputs and inclusion lists are initially generated just by
        looking at lines with differences.

        This adds non-anchored rex patterns for any overly suspicious
        strings found (host, username, dates etc.) that occur on lines
        that are not set as rex_inputs, removals or substrings.
        """
        specifics, common, removals = exc
        if debug:
            for (line, s) in specifics.items():
                print('SPECIFIC LINE IN %d: %s\n'
                      '  host: %s  ip: %s  cwd: %s  homedir: %s  tmpdir: %s'
                      '  user: %s  datelike: %s  dtlike: %s\n'
                      '  rex inputs: %s  remove: %s  substring: %s\n'
                      % (line, s.line.rstrip(),
                         s.host, s.ip, s.cwd, s.homedir, s.tmpdir,
                         s.user, bool(s.datelike), bool(s.dtlike),
                         bool(s.rex_inputs), bool(s.remove),
                         bool(s.substring)))
        rexes = extract(common)
        substrings = []
        self.exclusions[name] = (rexes, removals, substrings)

        for k in ('host', 'ip', 'cwd', 'user', 'homedir', 'tmpdir'):
            # need slightly different condition if cwd is in homedir
            if k == 'homedir' and self.cwd.startswith(self.homedir):
                f = lambda x: not x.cwd
            else:
                f = lambda x: 1
            if any(getattr(s, k, None) and not s.rex_inputs
                                       and not s.remove
                                       and not s.substring
                                       and f(s)
                   for s in specifics.values()):
                # Need this as an exclusion
                specific_string = getattr(self, k)
                if k == 'homedir':
                    warning = ("*** WARNING: Non-portable reference to "
                               "user's home dir (%s) found in %s"
                               % (specific_string, name))
                    self.warnings.append(warning)
                    if self.verbose:
                        print(warning)
                    # Defer warning to later
                else:
#                    rexes.append(re.escape(specific_string))
                    substrings.append(specific_string)
        specific_date_lines = [s for s in specifics.values()
                                 if s.datelike]  # and not s.rex_inputs
                                                 # and not s.remove
                                                 # and not s.substring]
        extradates = self.find_specific_dates(specific_date_lines)
        specific_dt_lines = [s for s in specifics.values()
                               if s.dtlike]  # and not s.rex_inputs
                                             # and not s.remove
                                             # and not s.substring]
        extradts = self.find_specific_datetimes(specific_dt_lines)
        if len(extradates) + len(extradts) < MAX_SPECIFIC_DATE_VARIANTS:
            extras = [e for e in (extradates + extradts)]
            substrings.extend(extras)
        else:
            extras = extract(extradates) + extract(extradts)
            rexes.extend(extras)
        if debug:
           print('OUT:\n  rexes: %s\nremoves: %s\nsubstrings: %s\n'
                 % (rexes, removals, substrings))

    def check_for_specific_references(self, path, filetype):
        """
        Finds references in the file at path that look to be
        over-specific to the details of the machine, user and time
        that the command is run.

        Returns an ordered dictionary, keyed on line number,
        with details of what (potentially) over-specific references
        were found on that line (only for affected lines).
        """
        specifics = OrderedDict()
        lines = protected_readlines(path, filetype)
        if lines:
            for i, line in enumerate(lines, 1):
                datelike = self.is_date_like(line, plausible=True)
                dtlike = False
                if datelike:
                    dtlike = is_datetime_like(line)
                    if dtlike:
                        datelike = False
                host = self.host in line
                ip = (self.ip_address in line) if self.ip_address else False
                cwd = self.cwd in line
                homedir = self.homedir in line
                tmpdir = self.tmp_dir_shell_var and TMPDIR in line
                if tmpdir:
                    self.tmpdir_used = True
                user = (self.user in line
                        and (not (homedir and self.user_in_home)))
                if any((datelike, dtlike, host, ip, cwd, homedir, tmpdir,
                        user)):
                    specifics[i] = Specifics(line, host, ip, cwd, homedir,
                                             tmpdir, user, datelike, dtlike)
        return specifics

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

    def fail_if_bad_exit_code(self, r):
        if r.exit_code != 0 and self.require_zero_exit_code:
            print('*** Non-zero exit code of %d generated by command.'
                  % r.exit_code, file=sys.stderr)
            if r.err:
                print('*** Output to stderr was:\n%s'
                      % r.err, file=sys.stderr)
            else:
                print('*** No output to stderr. Output to stdout was:\n%s'
                      % r.out, file=sys.stderr)
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
            print('Saved (%sempty) output to stdout to %s.'
                  % (('non-' if stdout_output else ''),
                     self.abs_or_rel(self.stdout_path(run))))

        if self.check_stderr:
            self.write_expected_output(stderr_output, self.stderr_path(run))
            print('Saved (%sempty) output to stderr to %s.'
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

    def remove_extra_reference_files(self):
        # Remove subdirs 2, 3, ..., N
        if self.iterations > 1:
            for run in range(2, self.iterations + 1):
                d = os.path.join(self.refdir, str(run))
                if os.path.exists(d):
                    shutil.rmtree(d)

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

    def ref_subdir(self):
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
            mapped_ref_path = ref_path
            suffix = 0
            while ref_path.lower() in ref_paths:
                if suffix:
                    ref_path = ref_path[:-len(str(suffix))]
                suffix += 1
                ref_path = ref_path + str(suffix)
                mapped_ref_path = self.ref_path(path) + str(suffix)
            if suffix:
                self.ref_map[path] = mapped_ref_path
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

    def write_expected_output(self, out, path, encoding=None):
        """
        Write the output (stdout or stderr) actually generated by
        (the first run of) command to a file for reference testing.
        """
        enc = get_encoding(path, encoding)
        with open(path, 'w', encoding=enc) as f:
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
        reference_files = self.reference_files[1]  # ones from run 1
        actual_paths = self.generated_file_paths()
        if any(istmpfile(p) for p in reference_files):
            self.tmpdir_used = True
        if self.tmpdir_used:
            set_tmpdir = ('\n    '.join([
                          '    orig_tmpdir = %s' % repr(TMPDIR),
                          "if not os.environ.get('TMPDIR_SET_BY_GENTEST'):",
                          '    tmpdir = tempfile.mkdtemp()',
                          "    os.environ['%s'] = tmpdir"
                               % self.tmp_dir_shell_var,
                          "    os.environ['TMPDIR_SET_BY_GENTEST'] = 'true'",
                          'else:',
                          "    tmpdir = os.environ['TMPDIR']",
                          '']))
        else:
            set_tmpdir = ''
        with open(self.script, 'w') as f:
            f.write(HEADER % {
                'SCRIPT': os.path.basename(self.script),
                'CLASSNAME': os.path.basename(self.raw_script[5:-3]).upper(),
                'GEN_COMMAND': self.cli_command(),
                'COMMAND': repr(self.command),
                'CWD': repr(self.cwd),
                'NAME': repr(self.ref_subdir()),
                'EXIT_CODE': r.exit_code,
                'SET_TMPDIR': set_tmpdir,
                'GENERATED_FILES': self.generated_files_var(),
                'REMOVE_PREVIOUS_OUTPUTS': self.remove_previous_outputs(),
            })
            if self.check_stdout:
                path = as_join_repr(self.stdout_path(), self.cwd,
                                    self.ref_subdir())
                exc = self.exclusions.get('STDOUT')
                (patterns, removals, substrings) = (exc if exc
                                                        else (None, None,
                                                              None))
                f.write(test_def('stdout', 'self.output', 'String', path,
                                 patterns, removals, substrings))
            if self.check_stderr:
                path = as_join_repr(self.stderr_path(), self.cwd,
                                    self.ref_subdir())
                exc = self.exclusions.get('STDERR')
                (patterns, removals, substrings) = (exc if exc else (None,
                                                                     None,
                                                                     None))
                f.write(test_def('stderr', 'self.error', 'String', path,
                                 patterns, removals, substrings))

            for path in reference_files:
                testname = self.test_name(path)
                ref_path = self.ref_map.get(path, self.ref_path(path))
                short_path = os.path.split(ref_path)[1]
                ref_path = as_join_repr(ref_path, self.cwd, self.ref_subdir())
                actual_path = as_join_repr(path, self.cwd, self.ref_subdir(),
                                           inc_tmpdir=True)
                exc = self.exclusions.get(short_path)
                filetype = (self.filetypes.get(short_path)
                                or FileType(short_path))
                if filetype.text:
                    if exc:
                        (patterns, removals, substrings) = exc
                    else:
                         patterns = removals = substrings = None
                    f.write(test_def(testname, actual_path, 'TextFile',
                                     ref_path, patterns, removals, substrings,
                                     encoding=filetype.encoding))
                else:
                    f.write(test_def(testname, actual_path, 'BinaryFile',
                                     ref_path))

            f.write(TAIL)
        print('\nTest script written as %s' % self.abs_or_rel(self.script))

    def generated_file_paths(self, in_cls=False):
        """
        List of generated files.
        """
        return [self.path_repr(ref_path, as_dollar=False, in_cls=in_cls)
                for ref_path in self.reference_files[1]]

    def generated_files_var(self):
        """
        Generates files GENERATED_FILES assignment, if needed,
        used by setUpClass to remove any outputs that are already there.
        """
        paths = self.generated_file_paths(in_cls=True)
        if paths:
            return ('    generated_files = [\n        %s\n    ]'
                    % (',\n    '.join(paths)))
        else:
            return ''

    def remove_previous_outputs(self):
        refs = self.reference_files[1]
        if not refs:
            return ''
        return ('for path in cls.generated_files:\n'
                '            if os.path.exists(path):\n'
                '                os.unlink(path)')

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
        exclusions = set([self.tmpdir]) if self.tmp_dir_shell_var else set()
        files += ' '.join(repr(f) for f in self.raw_files
                          if not f in exclusions)
        flags = []
        if not self.check_stdout:
            flags.append('--no-stdout')
        if not self.check_stderr:
            flags.append('--no-stderr')
        if zec is None:
            zec = self.require_zero_exit_code
        if not zec:
            flags.append('--non-zero-exit')
        if self.no_clobber:
            flags.append('--no-clobber')
        flags_string = ' '.join(flags + ['']) if flags else ''
        return ('tdda gentest %s%s %s'
                % (flags_string,
                   repr(self.command),
                   repr(os.path.basename(self.script)))
                + (files if files.strip() else ''))

    def summary(self, inc_timings=True):
        lines = ['']
        r = self.results[1]  # first run used as base copy to write
        reference_files = self.reference_files[1]
        n_tests = (len(reference_files)
                   + int(self.check_stdout)
                   + int(self.check_stderr)
                   + 2)  # exit code and no error
        if inc_timings:
            lines = [
                'Command execution took: %s' % format_time(r.duration)
            ]
        lines += [
            '',
            'SUMMARY:',
            '',
            'Directory to run in:        %s' % ('.' if self.relative_paths
                                                       else self.cwd),
            'Shell command:              %s' % self.command,
            'Test script generated:      %s' % self.script,
            'Reference files:%s' % ('' if reference_files
                                       else ' (none)'),
        ] + [
            '    %s' % self.path_repr(f) for f in reference_files

        ] + [
            'Check stdout:               %s'
            % stream_desc(self.check_stdout, r.out),
            'Check stderr:               %s'
            % stream_desc(self.check_stderr, r.err),
            'Expected exit code:         %d' % r.exit_code,
            'Clobbering permitted:       %s'
            % ('no' if self.no_clobber else 'yes'),
            'Number of times script ran: %d' % self.iterations,
            'Number of tests written:    %d' % n_tests,
            '',
        ]
        return '\n'.join(lines)

    def abs_or_rel(self, path):
        """
        Convenience function for as_join_repr with as_pwd=.
        """
        return (as_join_repr(path, self.cwd, as_pwd='.') if self.relative_paths
                                                         else path)

    def is_date_like(self, line, plausible=False, inc_alpha=True):
        if plausible:
            tm = self.min_time
            tM = self.max_time
        else:
            m = M = None
        line = line.rstrip()
        return is_date_like(line, inc_alpha, min_time=tm, max_time=tM)

    def find_specific_datetimes(self, specific_lines):
        """
        Find the actual plausible datetimes in the specific lines provided
        and return as a list.
        """
        extras = []
        for s in specific_lines:
            extras.extend(self.find_specific_datetimes_in_line(s.line))
        return extras

    def find_specific_datetimes_in_line(self, line):
        """
        Find the actual plausible datetimes in the line provided
        and return as a list.
        """
        m = is_datetime_like(line)
        if not m:
            return []
        start = m.start(2)
        end = m.end(8)
        dt_str = line[start:end]
        first = [dt_str]
        rest = line[end:]
        others = self.find_specific_datetimes_in_line(rest) if rest else []
        return first + others

    def find_specific_dates(self, specific_lines):
        """
        Find the actual plausible dates in the specific_lines provided
        that are NOT datetimes and return as a list.
        """
        extras = []
        for s in specific_lines:
            extras.extend(self.find_specific_dates_in_line(s.line))
        return extras

    def find_specific_dates_in_line(self, line):
        """
        Find the actual plausible dates in the line provided
        that are NOT datetimes and return as a list.
        """
        m = self.is_date_like(line, plausible=True)
        if not m:
            return []
        start = m.start(2)
        end = m.end(4)
        date_str = line[start:end]
        poss_dt_str = line[start:end + 15]
                      # 15 is enough for almost all time components;
                      # but not enough to contain another full datetime
        if not is_datetime_like(poss_dt_str):
            first = [date_str]
        else:
            first = []  # don't include dates that are part of datetimes
        rest = line[end:]
        others = self.find_specific_dates_in_line(rest) if rest else []
        return first + others

    def path_repr(self, path, as_dollar=True, in_cls=False):
        """
        Convenience function for as_join_repr with as_pwd=$(pwd)
        and inc_tmpdir set to True and as_tmpdir set to $TMPDIR
        or whatever the correct name is.
        """
        if self.tmp_dir_shell_var:
            if as_dollar:
                return as_join_repr(path, self.cwd, as_pwd='$(pwd)',
                                    inc_tmpdir=True,
                                    as_tmpdir='$%s' % self.tmp_dir_shell_var,
                                    in_cls=in_cls)
            else:
                return as_join_repr(path, self.cwd, inc_tmpdir=True,
                                    in_cls=in_cls)
        else:
            if as_dollar:
                return as_join_repr(path, self.cwd, as_pwd='$(pwd)',
                                    in_cls=in_cls)
            else:
                return as_join_repr(path, self.cwd, in_cls=in_cls)

    def fail(self, msg):
        print('FAILURE: ' + msg, file=sys.stderr)
        sys.exit(1)


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


def is_date_like(line, inc_alpha=True, min_time=None, max_time=None):
    if not re.match(D2, line):
        return None            # no 2-digit sequences in line
    line = line.lower()

    m = re.match(NUM_DATE_RE, line)
    if m:
        # group1 is the non-digit term
        n1, n2, n3 = int(m.group(2)), int(m.group(3)), int(m.group(4))
        n1_poss_day = 1 <= n1 <= 31
        n1_poss_month = 1 <= n1 <= 12

        n2_poss_day = 1 <= n2 <= 31
        n2_poss_month = 1 <= n2 <= 12

        n3_poss_day = 1 <= n3 <= 31

        if n1_poss_day and n2_poss_month:  # dd/mm/yyyy
            d = datetime.datetime(n3, n2, n1)
            if min_time is None or (d >= min_time and d <= max_time):
                return m

        if n3_poss_day and n2_poss_month:  # yyyy/mm/dd
            d = datetime.datetime(n1, n2, n3)
            if min_time is None or (d >= min_time and d <= max_time):
                return m

        if n2_poss_day and n1_poss_month:  # mm/dd/yyyy
            d = datetime.datetime(n3, n1, n2)
            if min_time is None or (d >= min_time and d <= max_time):
                return m

        return None

    elif not inc_alpha:
        return None

    m = re.match(EURO_STR_DATE_RE, line)
    if m:
        D, M, Y = int(m.group(2)), MONTH_MAP[m.group(3)[:3]], int(m.group(4))
        if not 1 <= D <= 31:
            return None
        d = datetime.datetime(Y, M, D)
        t = min_time is None or min_time <= d <= max_time
        return m if t else None

    m = re.match(US_STR_DATE_RE, line)
    if not m:
        return None
    M, D, Y = MONTH_MAP[m.group(2)[:3]], int(m.group(3)), int(m.group(4))
    if not (1 <= D <= 31):
        return None
    d = datetime.datetime(Y, M, D)
    t = min_time is None or min_time <= d <= max_time
    return m if t else None


def exec_command(command, cwd):
    """
    Execute the shell command given, in the directory specified as cwd.
    and return the various ouputs.
    """
    r = ExecuteCommand(command, cwd)
    return (r.out, r.err, r.exc, r.exit_code, r.duration)


def stream_desc(check, expected):
    L = len(expected)
    lines = len(expected.splitlines())
    was = ('empty' if L == 0
                   else repr(expected) if L < 40
                   else '%d line%s' % (lines, 's' if lines != 1 else ''))
    return '%s (was %s)' % ('yes' if check else 'no', was)


def is_datetime_like(line):
    """
    Check whether a line contains a datetime, currently assuming it
    is in an a forwards, backwards or confused-US-style date followed
    by a time.
    """
    if not re.match(D2, line):
        return None            # no 2-digit sequences in line
    line = line.strip().lower()
    return (re.match(NUM_DATETIME_RE, line)
            or re.match(EURO_STR_DATETIME_RE, line)
            or re.match(US_STR_DATETIME_RE, line))


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


def as_join_repr(path, cwd, name=None, as_pwd=None, inc_tmpdir=False,
                 as_tmpdir=None, in_cls=False):
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
                return os.path.join('%s%s%s' % (as_pwd, os.path.sep, tail))
            else:
                ref = os.path.join('ref', name) if name else 'ref'
                L = len(ref) + len(os.path.sep)
                if tail.startswith(ref + os.path.sep):
                    tail = tail[L:]
                    return 'os.path.join(self.refdir, %s)' % repr(tail)
                else:
                    prefix = '' if in_cls else 'self.'
                    return 'os.path.join(%scwd, %s)' % (prefix, repr(tail))
    if inc_tmpdir:
        tmpdir = TMPDIR + os.path.sep
        if istmpfile(path):
            L = len(TERM_TMPDIR)
            tail = path[L:]
            if as_tmpdir:
                return '%s%s%s' % (as_tmpdir, os.path.sep, tail)
            else:
                prefix = '' if in_cls else 'self.'
                return 'os.path.join(%stmpdir, %s)' % (prefix, repr(tail))
    return repr(path)


def istmpfile(path):
    return path.startswith(TERM_TMPDIR)


def test_def(name, actual, kind, ref_file_path, patterns=None, removals=None,
             substrings=None, encoding=None):
    """
    returns a ReferenceTestCase-style test as a string.
    """
    lines = ['', 'def test_%s(self):' % name]
    extras = []
    assert kind in ('TextFile', 'String', 'BinaryFile')
    assert_fn = 'self.assert%sCorrect' % kind
    spc = ' ' * (len(assert_fn) + 5)
    if patterns:
        lines.append('    patterns = [')
        for p in patterns:
            lines.append('        %s,' % quote_raw(p))
        lines.append('    ]')
        extras.append(spc + 'ignore_patterns=patterns')
    if substrings:
        lines.append('    substrings = [')
        ss = ['self.orig_tmpdir' if s == TMPDIR else repr(s)
              for s in substrings]
        for s in sorted(set(ss)):
            lines.append('        %s,' % s)
        lines.append('    ]')
        rspc = '' if extras else spc
        extras.append(rspc + 'ignore_substrings=substrings')
    if removals:
        lines.append('    removals = [')
        for p in removals:
            lines.append('        %s,' % repr(p))
        lines.append('    ]')
        rspc = '' if extras else spc
        extras.append(rspc + 'remove_lines=removals')
    if encoding is not None and kind == 'TextFile':
        rspc = '' if extras else spc
        extras.append(rspc + "encoding='%s'" % encoding)
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
    """
    Repeatedly prompts with msg until a yes/no response is generated.

    Returns True for Yes and False for No.
    """
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


def get_int(msg, default, minval=None, maxval=None):
    done = False
    while not done:
        reply = getline('%s?: [%d]' % (msg, default)).strip()
        if reply == '':
            n = default
            done = True
        try:
            n = int(reply)
            if ((minval is None or n >= minval)
                   and (maxval is None or n <= maxval)):
                done = True
        except:
            pass
    return n


def home_dir():
    """
    Returns user's home directory.
    """
    if 'HOME' in os.environ:
        return os.environ['HOME']
    elif is_unix():
        return os.path.expanduser('~')
    elif is_windows():
        from win32com.shell import shellcon, shell  # type: ignore
        return shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)


def is_unix():
    return os.name == 'posix'


def is_windows():
    return os.name == 'nt'


def ensure_py(name):
    return name if name.endswith('.py') else name + '.py'


def format_time(duration):
    """
    Format time in seconds, with at least two significant figures
    """
    dps = 2
    while dps < 10 and duration < pow(10, -dps + 1):
        dps += 1
    return ('%%.%dfs' % dps) % duration


def wizard(iterations):
    """
    Gather test specification from users with Q-and-A interface
    """
    shellcommand = getline('Enter shell command to be tested', empty_ok=False)
    output_script = getline('Enter name for test script', empty_ok=False,
                            default='test_' + sanitize_string(shellcommand))
    reference_files = []
    check_cwd = yes_no('Check all files written under $(pwd)')
    check_tmpdir = yes_no("Check all files written under (gentest's) $TMPDIR")
    tmp_dir_shell_var = DEFAULT_TMP_DIR_SHELL_VAR if check_tmpdir else None
    if check_cwd:
        reference_files.append('.')
    print('Enter other files/directories to be checked, one per line, then a blank line:')
    ref = getline()
    while ref:
        reference_files.append(ref)
        ref = getline()
    check_stdout = yes_no('Check stdout')
    check_stderr = yes_no('Check stderr')
    require_zero_exit_code = yes_no('Exit code should be zero')
    no_clobber = not(yes_no('Clobber (overwrite) previous outputs '
                            '(if they exist)'))
    iterations = get_int('Number of times to run script', iterations,
                         1, None)
    return (shellcommand, output_script, reference_files,
            check_stdout, check_stderr, require_zero_exit_code, no_clobber,
            iterations, tmp_dir_shell_var)


def gentest_parser(usage=''):
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog='tdda gentest',
                                     epilog=usage + GENTEST_HELP,
                                     formatter_class=formatter)
    parser.add_argument('-?', '--?', action='help',
                        help='Same as -h or --help')
    parser.add_argument('-m', '--max-files', type=int,
                        help='Max files to track')
    parser.add_argument('-r', '--relative-paths', action='store_true',
                        help='Show relative paths wherever possible')
    parser.add_argument('-n', '--iterations', type=int,
                        help='Number of times to run the command (default 2)')
    parser.add_argument('-O', '--no-stdout', action='store_true',
                        help='Do not generate a test checking output'
                             ' to STDOUT')
    parser.add_argument('-E', '--no-stderr', action='store_true',
                        help='Do not generate a test checking output'
                             ' to STDERR')
    parser.add_argument('-Z', '--non-zero-exit', action='store_true',
                        help='Do not require exit status to be 0')
    parser.add_argument('-C', '--no-clobber', action='store_true',
                        help='Do not overwrite existing test script or '
                             'reference directory')
    return parser


def gentest_flags(parser, args, params):
    flags, more = parser.parse_known_args(args)
    if flags.max_files:
        params['max_files'] = flags.max_files
    if flags.relative_paths:
        params['relative_paths'] = True
    if flags.iterations:  # None and zero both get default (2)
        params['iterations'] = flags.iterations
    if flags.no_stdout:
        params['no_stdout'] = True
    if flags.no_stderr:
        params['no_stderr'] = True
    if flags.non_zero_exit:
        params['non_zero_exit'] = True
    if flags.no_clobber:
        params['no_clobber'] = True
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
    script = positional_args[1] if len(positional_args) > 1 else None
    gentest(command, script, reference_files, **kw)


def gentest(shellcommand, output_script, reference_files,
            max_snapshot_files=MAX_SNAPSHOT_FILES, relative_paths=False,
            iterations=2, tmp_dir_shell_var=DEFAULT_TMP_DIR_SHELL_VAR,
            no_stdout=False, no_stderr=False, non_zero_exit=False,
            no_clobber=False):
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
         require_zero_exit_code,
         no_clobber,
         iterations,
         tmp_dir_shell_var) = wizard(iterations)
    else:
        check_stdout = not no_stdout
        check_stderr = not no_stderr
        require_zero_exit_code = not non_zero_exit
    cwd = os.getcwd()
    if shellcommand is None:
        print('\n*** USAGE:\n  %s' % USAGE, file=sys.stderr)
        sys.exit(1)
    if not output_script or output_script == '-':
        output_script = 'test_' + sanitize_string(shellcommand)
    lcrefs = [f.lower() for f in reference_files]
    if not lcrefs:
        reference_files = reference_files + ['.',]
    TestGenerator(cwd, shellcommand, output_script, reference_files,
                  check_stdout, check_stderr, require_zero_exit_code,
                  no_clobber, max_snapshot_files=max_snapshot_files,
                  relative_paths=relative_paths, iterations=iterations,
                  tmp_dir_shell_var=tmp_dir_shell_var)


if __name__ == '__main__':
    gentest_wrapper(sys.argv[1:])
