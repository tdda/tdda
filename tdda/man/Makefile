TARGETS = tdda.txt \
          tdda-discover.txt \
          tdda-detect.txt \
          tdda-diff.txt \
          tdda-examples.txt \
          tdda-gentest.txt \
          tdda-help.txt \
          tdda-serial.txt \
          tdda-verify.txt \
          tdda-version.txt

all: clean $(TARGETS)

clean:
	rm -f *.1 *.txt

$(TARGETS): %.txt: %.md
	go-md2man -in $< -out $*.1
	cat $*.1 | python sideheads.py | groff -Tutf8 > $@
	cp $*.1 /usr/local/man/man1
	python clean_markdown.py $*.md ../../doc/source/$*.md

PHONY:
svg:
	(cd ../referencetest; GENSVG=1 python testtddadiff.py)
