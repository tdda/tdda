-- script for creating the example.db sqlite file
--
-- usage:
--    sqlite3 example.db
--    (then paste in all of this file)


CREATE TABLE elements(
  "z" INTEGER,
  "name" TEXT,
  "symbol" TEXT,
  "period" INTEGER,
  "group_" INTEGER,
  "chemicalseries" TEXT,
  "atomicweight" REAL,
  "etymology" TEXT,
  "relativeatomicmass" REAL,
  "meltingpointc" REAL,
  "meltingpointkelvin" REAL,
  "boilingpointc" REAL,
  "boilingpointf" REAL,
  "density" REAL,
  "description" TEXT,
  "colour" TEXT
);

.mode csv elements
.import /tmp/elements_data2.csv elements

update elements set z = NULL where z = '\N';
update elements set name = NULL where name = '\N';
update elements set symbol = NULL where symbol = '\N';
update elements set period = NULL where period = '\N';
update elements set group_ = NULL where group_ = '\N';
update elements set chemicalseries = NULL where chemicalseries = '\N';
update elements set atomicweight = NULL where atomicweight = '\N';
update elements set etymology = NULL where etymology = '\N';
update elements set relativeatomicmass = NULL where relativeatomicmass = '\N';
update elements set meltingpointc = NULL where meltingpointc = '\N';
update elements set meltingpointkelvin = NULL where meltingpointkelvin = '\N';
update elements set boilingpointc = NULL where boilingpointc = '\N';
update elements set boilingpointf = NULL where boilingpointf = '\N';
update elements set density = NULL where density = '\N';
update elements set description = NULL where description = '\N';
update elements set colour = NULL where colour = '\N';

