serialformat.html: serialformat.md
	multimarkdown -bf serialformat.md


serialformat.md: tdda.serial.md dd
	chmod -f 644 serialformat.md
	python inclusions.py tdda.serial.md serialformat.md
	chmod 444 serialformat.md


.PHONY:
dd:
	(cd docdata; make)

