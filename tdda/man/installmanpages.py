import os
import shutil
import sys


MANDIR = os.path.dirname(__file__)
LOCAL_MAN_DIR = os.path.expanduser('~/.local/share/man/man1')
SYSTEM_MAN_DIR = '/usr/local/share/man/man1'

MANPATH_LINE = 'export MANPATH="$HOME/.local/share/man:$MANPATH"'

SHELL_CONFIGS = ['~/.zshrc', '~/.bash_profile', '~/.bashrc']

WINDOWS_MESSAGE = '''
Man pages are not supported on Windows.
Consider running tdda under WSL (Windows Subsystem for Linux).
'''.strip()

HELP_MESSAGE = '''
Usage: tdda installman [--system]

Installs tdda man pages.

  --system, -s   Install system-wide to /usr/local/share/man/man1
                 (may require sudo)

Without --system, installs to ~/.local/share/man/man1.
'''.strip()


def install_man_pages(system=False):
    if sys.platform == 'win32':
        print(WINDOWS_MESSAGE, file=sys.stderr)
        sys.exit(1)

    dest = SYSTEM_MAN_DIR if system else LOCAL_MAN_DIR

    if not os.path.exists(dest):
        try:
            os.makedirs(dest)
        except PermissionError:
            print(
                f'Cannot create {dest}: permission denied.\n'
                'Try running with sudo, or omit --system for a local install.',
                file=sys.stderr
            )
            sys.exit(1)

    if not os.access(dest, os.W_OK):
        print(
            f'Cannot write to {dest}: permission denied.\n'
            'Try running with sudo, or omit --system for a local install.',
            file=sys.stderr
        )
        sys.exit(1)

    man_files = [
        f for f in os.listdir(MANDIR) if f.endswith('.1')
    ]

    if not man_files:
        print('No man page files found.', file=sys.stderr)
        sys.exit(1)

    for fname in man_files:
        src = os.path.join(MANDIR, fname)
        dst = os.path.join(dest, fname)
        shutil.copy2(src, dst)

    print(f'Installed {len(man_files)} man pages to {dest}.')

    if not system and sys.platform == 'darwin':
        manpath = os.environ.get('MANPATH', '')
        local = os.path.expanduser('~/.local/share/man')
        if local not in manpath:
            configs = ', '.join(SHELL_CONFIGS)
            print(
                f'\nTo use these man pages, add the following line to your '
                f'shell config\n(e.g. {configs}):\n\n'
                f'  {MANPATH_LINE}\n\n'
                'The man pages should then be available in new shells.'
            )


def install_man_pages_cli(args):
    if '--help' in args or '-h' in args or '-?' in args:
        print(HELP_MESSAGE)
        return
    system = '--system' in args or '-s' in args
    install_man_pages(system=system)
