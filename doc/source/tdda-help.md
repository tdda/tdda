### Command: `tdda help`


#### NAME

`tdda help` - Provides help on `tdda` and its sub-commands.

#### SYNOPSIS
```x
tdda help
tdda help COMMAND
```
#### POSITIONAL ARGUMENTS

*COMMAND* can be any of:

 - `discover`
 - `verify`
 - `detect`

 - `gentest`
 - `diff`
 - `examples`

 - `help`
 - `version`

#### DESCRIPTION

Shows help on a tdda subcommand or topic.

Taking inspiration from `git`, if the man pages are installed,
help on main commands can be obtained with

   `man tdda-COMMAND`

For example:

   `man tdda-discover`

Help can also be obtained on each command with `--help`, `-h` or `-?`, e.g.

   `tdda discover --help`

####  EXAMPLES

`tdda help`               Shows this help

`tdda help gentest`       Shows help on gentest
