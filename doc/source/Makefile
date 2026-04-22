serialformat.html: serialformat.md
	multimarkdown -bf serialformat.md


serialformat.md: tdda.serial.md docdata/docdata-output.txt
	python inclusions.py tdda.serial.md serialformat.md


.PHONY:
docdata/docdata-output.txt:
	(cd docdata; make)

