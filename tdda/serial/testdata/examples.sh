#!/bin/sh
set -e -x
tdda serial --gen semicolon.txt semicolon.serial
tdda serial --gen semicolon2.txt semicolon2.serial
tdda serial --gen semicolon3.txt semicolon3.serial
#tdda serial --gen semicolon4.txt semicolon4.serial
tdda serial --gen semicolon5.txt semicolon5.serial
tdda serial --gen semicolon6.txt semicolon6.serial

tdda serial --gen onebool.txt onebool.serial --single
tdda serial --gen onereal.txt onereal.serial -1
tdda serial --gen onestring.txt onestring.serial -1
