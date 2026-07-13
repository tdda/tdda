DATE    = July 2026
VERSION = 3.3

TARGETS = tdda.txt \
          tdda-discover.txt \
          tdda-detect.txt \
          tdda-diff.txt \
          tdda-examples.txt \
          tdda-gentest.txt \
          tdda-help.txt \
          tdda-ls.txt \
          tdda-cat.txt \
          tdda-head.txt \
          tdda-tail.txt \
          tdda-sample.txt \
          tdda-serial.txt \
          tdda-tag.txt \
          tdda-verify.txt \
          tdda-version.txt \
          tdda-config.txt \
          tdda-test.txt \
          tdda-installman.txt \
          rexpy.txt \
          xerpy.txt


CLI_SRCS = sphinx/tdda.md \
           sphinx/tdda-discover.md \
           sphinx/tdda-verify.md \
           sphinx/tdda-detect.md \
           sphinx/tdda-diff.md \
           sphinx/tdda-ls.md \
           sphinx/tdda-cat.md \
           sphinx/tdda-head.md \
           sphinx/tdda-tail.md \
           sphinx/tdda-sample.md \
           sphinx/tdda-serial.md \
           sphinx/tdda-gentest.md \
           sphinx/tdda-tag.md \
           sphinx/tdda-examples.md \
           sphinx/tdda-version.md \
           sphinx/tdda-config.md \
           sphinx/tdda-test.md \
           sphinx/tdda-help.md \
           sphinx/tdda-installman.md \
           sphinx/rexpy.md \
           sphinx/xerpy.md

all: clean sphinx $(TARGETS) cli

sphinx:
	mkdir -p sphinx

cli: $(CLI_SRCS)
	python make_cli.py ../../doc/source/cli.md $(CLI_SRCS)

clean:
	rm -f *.1 *.txt sphinx/*.md

tdda-config.md: tdda-config.md.in gen_config_params.py
	python preprocess.py tdda-config.md.in tdda-config.md

$(TARGETS): %.txt: %.md
	sed 's|%%DATE%%|$(DATE)|g; s|%%VERSION%%|$(VERSION)|g' $< > $*.md.tmp
	go-md2man -in $*.md.tmp -out $*.1
	rm $*.md.tmp
	cat $*.1 | python sideheads.py | groff -Tutf8 > $@
	cp $*.1 /usr/local/man/man1
	python clean_markdown.py $*.md sphinx/$*.md

PHONY:
svg:
	(cd ../referencetest; GENSVG=1 python testtddadiff.py)
