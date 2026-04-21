serialformat.html: serialformat.md
	multimarkdown -bf serialformat.md


serialformat.md: tdda.serial.md data/docdata-output.txt
	python inclusions.py tdda.serial.md serialformat.md


.PHONY:
data/docdata-output.txt:
	(cd data; make)

