serialformat.html: serialformat.md
	multimarkdown -bf serialformat.md


serialformat.md: tdda.serial.md dd
	python inclusions.py tdda.serial.md serialformat.md


.PHONY:
dd:
	(cd docdata; make)

