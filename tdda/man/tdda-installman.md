# "TDDA INSTALLMAN" 1 "%%DATE%%" "%%VERSION%%" "tdda installman manual"

## NAME

`tdda installman` — install tdda man pages

## SYNOPSIS

`tdda installman` [--system]

## DESCRIPTION

Installs the `tdda` man pages so they can be accessed with the `man` command.

Once installed, the main `tdda` man page is available as:

man tdda

Man pages for `tdda` subcommands are available as:

`man tdda-COMMAND`

For example:

`man tdda-discover`  
`man tdda-gentest`

The `rexpy` and `xerpy` man pages are accessed as:

`man rexpy`  
`man xerpy`

By default, man pages are installed to `~/.local/share/man/man1`.
On MacOS, this directory may not be in the default man search path;
if so, `tdda installman` will print the line to add to your shell
config file to make the man pages available in new shells.

With `--system`, man pages are installed to `/usr/local/share/man/man1`,
which is in the default search path on most systems but may require
running with `sudo`.

On Windows, man pages are not supported; consider running `tdda` under
WSL (Windows Subsystem for Linux).

## OPTIONS

`--system`, `-s`  
  Install system-wide to `/usr/local/share/man/man1` (may require sudo).

## EXAMPLES

1) `tdda installman`  
   Install man pages to `~/.local/share/man/man1`.

2) `tdda installman --system`  
   Install man pages system-wide (may require sudo).

## SEE ALSO

`tdda-help(1)`
