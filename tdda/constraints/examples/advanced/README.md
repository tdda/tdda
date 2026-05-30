# Example of extending the tdda.constraints module

[This is only intended for people wanting to extend TDDA.
This is not for normal end users of the command-line tools
or the TDDA Python API.]

The `files_extension.py` file contains Python source code for a very simple
implementation of a (not very realistic or useful) extension to the
`tdda.constraints` module.

The extension provides the ability to do constraint discovery and
verification on directory/folder filesystem structure (the names and
sizes of files).

Run all commands from this directory (`cd advanced`).

To enable this extension, add the following to your environment.

For Linux, MacOS and other Unix systems:

    export TDDA_EXTENSIONS=files_extension.TDDAFilesExtension
    export PYTHONPATH=.:$PYTHONPATH

For Microsoft Windows:

    set TDDA_EXTENSIONS=files_extension.TDDAFilesExtension
    set PYTHONPATH=.;$PYTHONPATH

Then you can discover constraints on all the example files in this directory
with:

1. Discover constraints on the files in the current directory:

        tdda discover . files.tdda

   This should produce a set of constraints on the names and sizes of the
   files in this directory, and write these to the file `files.tdda`.

2. Verify those constraints:

        tdda verify . files.tdda

   This should pass.

3. Create a new file with a name longer than any existing filename, and
   reverify:

        touch this-filename-is-quite-a-lot-longer-than-the-others.txt
        tdda verify . files.tdda

   Now the `max_length` constraint on the `name` field should fail.
   (The `size` constraints will also fail, since `touch` creates an empty file.)
