# Configuration

Various aspects of the behaviour of the TDDA Library can be configured
by storing settings in a configuration file.

## Location of configuration file

The configuration file is called `.tdda.toml` in the home directory
(i.e. `~` or `$HOME` on Unix-like and Linux systems, including Macs, and `%USERPROFILE%`
on Windows).

## Format

The configuration file is a [TOML](https://toml.io) file, with different
sections for different areas of the software.

## Status

The number of configurable variables is currently limited, but is expected
to expand over time.

## Override

Most of the command line tools accept `--no-config` to suppress loading
of the configuration file, i.e. to use the `tdda` defaults.

Most settings in the configuration file also have command-line switches
to control the behaviour, usually with closely related names.
Command-line switches override configuration settings.

Similarly, many API calls accept a config object which, if supplied,
will be used instead of the settings in the configuration file.
A configuration file with default settings can be obtained with

```
from tdda.config import Config

config = Config(load=False)
```

If the `load=False` parameter is not set, a `Config()` object with
the user‘s configuration will be loaded.

In either case, the configuration can be modified after load. This will
not alter the configuration file.







