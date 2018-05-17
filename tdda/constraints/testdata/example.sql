-- script for creating the example.db sqlite file
--
-- take a copy of elements118.csv, and then:
--    a) remove the header line
--    b) replace all the null values with \N (that's everything between
--       adjacent commas, and after any trailing comma at the end of a line)
--    c) insert a _rowindex column at the start (numbers starting at 0)
--    d)and then save it as example.csv.
--
-- then run:
--
--    rm example.db
--    sqlite3 example.db
--
-- (and paste in all of this file)


CREATE TABLE elements(
  "_rowindex" INTEGER,
  "Z" INTEGER,
  "Name" TEXT,
  "Symbol" TEXT,
  "Period" INTEGER,
  "Group" INTEGER,
  "ChemicalSeries" TEXT,
  "AtomicWeight" REAL,
  "Etymology" TEXT,
  "RelativeAtomicMass" REAL,
  "MeltingPointC" REAL,
  "MeltingPointKelvin" REAL,
  "BoilingPointC" REAL,
  "BoilingPointF" REAL,
  "Density" REAL,
  "Description" TEXT,
  "Colour" TEXT
);

.mode csv elements
.import example.csv elements

update elements set Z = NULL where Z = '\N';
update elements set Name = NULL where Name = '\N';
update elements set Symbol = NULL where Symbol = '\N';
update elements set Period = NULL where Period = '\N';
update elements set "Group" = NULL where "Group" = '\N';
update elements set ChemicalSeries = NULL where ChemicalSeries = '\N';
update elements set AtomicWeight = NULL where AtomicWeight = '\N';
update elements set Etymology = NULL where Etymology = '\N';
update elements set RelativeAtomicMass = NULL where RelativeAtomicMass = '\N';
update elements set MeltingPointc = NULL where MeltingPointC = '\N';
update elements set MeltingPointKelvin = NULL where MeltingPointKelvin = '\N';
update elements set BoilingPointC = NULL where BoilingPointC = '\N';
update elements set BoilingPointF = NULL where BoilingPointF = '\N';
update elements set Density = NULL where Density = '\N';
update elements set Description = NULL where Description = '\N';
update elements set Colour = NULL where Colour = '\N';

