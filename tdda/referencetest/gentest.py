# -*- coding: utf-8 -*-

"""
gentest.py: Automatic test generation for test-driven data analysis
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


import os
import shutil
import sys
import subprocess
import tempfile

is_python3 = sys.version_info.major >= 3
actual_input = input if is_python3 else raw_input

from tdda.referencetest.gentest_boilerplate import (HEADER, TAIL, STDOUT,
                                                    STDERR, REFTEST)

USAGE = '''python gentest.py 'quoted shell command' test_outputfile.py [reference files]'''


def gentest(shellcommand=None, output_script=None, *reference_files):
    """
    Generate code python in output_script for running the
    shell command given and checking the reference files
    provided (optionally including stdout as '-').

    If no reference files are provided, check stdout.

    By default, always check stderr.
    """
    if shellcommand is None and output_script is None:
        (shellcommand,
         output_script,
         reference_files,
         check_stdout,
         check_stderr) = wizard()
    else:
        check_stdout = None
        check_stderr = True
    cwd = os.getcwd()
    if shellcommand is None or output_script is None:
        print('\n*** USAGE:\n  %s' % USAGE, file=sys.stderr)
        sys.exit(1)
    print('\n\n$(pwd): %s  (used as default for $TDDA_CWD)' % cwd)
    print('Shell command: %s' % repr(shellcommand))
    output_test_script = force_start(canonicalize(output_script, '.py'),
                                     'test', 'test_')
    print('Output file: %s' % repr(output_test_script))
    files = [canonicalize(f) for f in reference_files if f != '-']
    print('References files to be checked: %s'
          % ''.join('\n  %s' % as_join_repr(f, cwd, True) for f in files))
    if check_stdout is None:
        check_stdout = len(reference_files) == 0 or '-' in reference_files
    print('Output to stdout %s be checked.'
          % ('WILL' if check_stdout else 'will NOT'))
    print('Output to stderr %s be checked.'
          % ('WILL' if check_stderr else 'will NOT'))
    TestGenerator(cwd, shellcommand, output_test_script, files,
                  check_stdout, check_stderr)


class TestGenerator:
    def __init__(self, cwd, command, script, reference_files, check_stdout,
                 check_stderr=True):
        self.cwd = cwd
        self.command = command
        self.script = script
        self.reference_files = reference_files
        self.check_stdout = check_stdout
        self.check_stderr = check_stderr

        self.refdir = os.path.join(self.cwd, 'ref')

        self.test_names = set()
        self.test_qualifier = 1

        print('\nRunning command %s to generate output.\n'
              % repr(self.command))
        out, err, exc = exec_command(self.command, self.cwd)
        self.create_ref_dir()
        if self.check_stdout:
            self.write_expected_output(out, self.stdout_path())
        if self.check_stderr:
            self.write_expected_output(err, self.stderr_path())
        if exc is not None:
            print('***ERROR: Exception occurred running command.\n%s.'
                  % str(exc), sys.stderr)
            sys.exit(1)
        if err:
            print('*** WARNING: There was output on stderr as follows:\n%s'
                  % err)
            if self.check_stderr:
                print('\n*** This will be used as the reference output '
                      'for stderr in %s.\n'
                      % as_join_repr(self.stderr_path(), self.cwd, True))
            else:
                print('\n*** WARNING: This is not being checked.\n'
                      '  Output on stderr will not cause a test failure.\n')
        elif self.check_stderr:
            print('Generated %s.\n'
                  '  It is EMPTY, as no output was produced on stderr.\n'
                  % as_join_repr(self.stderr_path(), self.cwd, True))
        if self.check_stdout:
            print('Generated %s.\n'
                  '  It is %s.'
                  % (self.stdout_path(), 'non-empty' if out else 'empty'))
        print()
        self.copy_reference_files()
        self.write_script()

    def create_ref_dir(self):
        if not os.path.exists(self.refdir):
            os.mkdir(self.refdir)

    def copy_reference_files(self):
        """
        Copy files specified to ref subdirectory.
        """
        ref_paths = set()
        for path in self.reference_files:
            ref_path = self.ref_path(path)
            if ref_path in ref_paths:
                print('Multiple files with same (base) name %s.\n'
                      'Cannot yet handle this case.'
                      % os.path.basename(ref_name), file=sys.stderr)
                sys.exit(1)
            ref_paths.add(ref_path)
            shutil.copyfile(path, ref_path)
            print('Copied %s to %s' % (as_join_repr(path, self.cwd, True),
                                       as_join_repr(ref_path, self.cwd, True)))

    def write_expected_output(self, out, path):
        """
        Write the output (stdout or stderr) actually generated by
        (the first run of) command to a file for reference testing.
        """
        with open(path, 'w') as f:
            f.write(out)

    def stdout_path(self):
        """
        Path to write stdout to, if it is being checked.
        """
        name = os.path.splitext(os.path.basename(self.script))[0]
        return self.ref_path('stdout_for_%s' % name)

    def stderr_path(self):
        """
        Path to write stderr to, if it is being checked.
        """
        name = os.path.splitext(os.path.basename(self.script))[0]
        return self.ref_path('stderr_for_%s' % name)

    def ref_path(self, path):
        """
        Returns the location for the reference file corresponding
        to the (original) path provided.
        """
        return os.path.join(self.refdir, os.path.basename(path))

    def write_script(self):
        """
        Generate the test script.
        """
        with open(self.script, 'w') as f:
            f.write(HEADER % (os.path.basename(self.script),
                              repr(self.command), repr(self.cwd)))
            if self.check_stdout:
                f.write(STDOUT % as_join_repr(self.stdout_path(), self.cwd))
            if self.check_stderr:
                f.write(STDERR % as_join_repr(self.stderr_path(), self.cwd))
            for path in self.reference_files:
                testname = self.test_name(path)
                f.write(REFTEST % (testname, as_join_repr(path, self.cwd),
                                   as_join_repr(self.ref_path(path), self.cwd)))
            f.write(TAIL)
        print('\nTest script written as %s' % self.script)


    def test_name(self, path):
        """
        Generates a test name corresponding to the path provided.
        """
        name = os.path.basename(path)
        testname = ''.join(c if c.isalnum() else '_' for c in name)
        if testname in self.test_names:
            self.test_qualifier += 1
            testname += str(len(self.test_qualifier))
        self.test_names.add(testname)
        return testname


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


def as_join_repr(path, cwd, as_pwd=False):
    if cwd.endswith(os.path.sep):
        cwd = cwd[:-len(os.path.sep)]
    if path.startswith(cwd + os.path.sep):
        if path not in (cwd, cwd + os.path.sep):
            tail = path[len(cwd):]
            if os.path.isabs(tail):
                tail = tail[1:]
            if as_pwd:
                return '$(pwd)/%s' % tail
            else:
                if tail.startswith('ref' + os.path.sep):
                    tail = tail[3 + len(os.path.sep):]
                    return "os.path.join(CWD, 'ref', %s)" % repr(tail)
                else:
                    return 'os.path.join(CWD, %s)' % repr(tail)
    return repr(path)


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


def exec_command(command, cwd):
    """
    Executes command, with cwd as provided, in a subprocess.

    Returns a 2-tuple consisting of the output to stdout and to stderr.
    """
    out = err = exc = None
    try:
        sp = subprocess.Popen(command, stdin=None,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, shell=True,
                              cwd=cwd, close_fds=True, env=os.environ)
        out, err = sp.communicate()
        if is_python3:
            out = out.decode('UTF-8')
            err = err.decode('UTF-8')
    except Exception as exc:
        pass
    return out, err, exc


def getline(prompt='', empty_ok=True):
    """
    Get a line from the user.

    Repeatedly issues the prompt given (if any) until the stripped input
    is non-empty, unless empty_ok is set.

    In either case, returns the stripped line provided.
    """
    done = False
    while not done:
        if prompt:
            print(prompt, end=' ')
        line = actual_input().strip()
        done = empty_ok or line
    return line


def wizard_for_stream(stream):
    assert stream in ('stdout', 'stderr')
    check = None
    while check is None:
        reply = getline('Check %s?: [y/n]' % stream).lower()
        if reply in ('y', 'yes'):
            check = True
        elif reply in ('n', 'no'):
            check = False
    return check


def wizard():
    shellcommand = getline('Enter shell command to be tested:', empty_ok=False)
    output_script = getline('Enter name for test script:', empty_ok=False)
    reference_files = []
    print('Enter files to be checked, one per line, then blank line')
    ref = getline()
    while ref:
        reference_files.append(ref)
        ref = getline()
    check_stdout = wizard_for_stream('stdout')
    check_stderr = wizard_for_stream('stderr')
    return (shellcommand, output_script, reference_files,
            check_stdout, check_stderr)


if __name__ == '__main__':
    gentest(*sys.argv[1:])
