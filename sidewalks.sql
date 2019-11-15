alter table SidewalkArea drop column width;
alter table SidewalkArea drop column area;
alter table SidewalkArea alter column adacomply type boolean using (adacomply = 'Yes');
alter table SidewalkArea alter column covered type boolean using (covered = 'Yes');

create table split_sidewalks as with union_sidewalks as (select adacomply, covered, ST_Union(geom) as geom from SidewalkArea group by adacomply, covered) select adacomply, covered, (ST_Dump(geom)).geom as geom from union_sidewalks;
alter table split_sidewalks add column gid bigserial;
alter table split_sidewalks alter column gid type integer;
create table bad as with rings as (select ST_ExteriorRing((ST_DumpRings(geom)).geom) as geom, gid from split_sidewalks) select distinct A.gid from rings as A join rings as B on A.gid = B.gid and not (A.geom = B.geom) and ST_Intersects(A.geom, B.geom);
delete from split_sidewalks using bad where split_sidewalks.gid=bad.gid;
drop table bad;
create table medians as select adacomply, covered, ST_ApproximateMedialAxis(geom) as geom from split_sidewalks;
create table linestrings as with lines as (select adacomply, covered, (ST_Dump(geom)).geom as geom from medians) select adacomply, covered, (ST_Dump(ST_LineMerge(ST_Union(geom)))).geom as geom from lines group by adacomply, covered;
alter table linestrings add column gid bigserial;
alter table linestrings alter column gid type integer;
create table endpoints as select ST_StartPoint(geom) as geom, adacomply, covered, gid as lineid, ST_Length(geom) as len from linestrings union select ST_EndPoint(geom) as geom, adacomply, covered, gid as lineid, ST_Length(geom) as len from linestrings;
create index on endpoints using GIST(geom);
insert into linestrings (adacomply, covered, geom) select a.adacomply and b.adacomply, a.covered, ST_MakeLine(a.geom, b.geom) as geom from endpoints as a join endpoints as b on ST_DWithin(a.geom, b.geom, 5) and not (a.geom = b.geom) and a.covered = b.covered where a.len > 10 and b.len > 10;
create table linestrings2 as with lines as (select adacomply, covered, (ST_Dump(geom)).geom as geom from linestrings) select adacomply, covered, (ST_Dump(ST_LineMerge(ST_Union(geom)))).geom as geom from lines group by adacomply, covered;

