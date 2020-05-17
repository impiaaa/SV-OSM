alter table SidewalkArea drop column width;
alter table SidewalkArea drop column area;
alter table SidewalkArea alter column adacomply type boolean using (adacomply = 'Yes');
alter table SidewalkArea alter column covered type boolean using (covered = 'Yes');

-- union sidewalk geometries by attributes, then split again, to normalize
create temporary table split_sidewalks as
  with union_sidewalks as
    (select adacomply, covered, ST_UnaryUnion(ST_Collect(geom)) as geom
     from SidewalkArea
     group by adacomply, covered)
    select adacomply, covered, (ST_Dump(geom)).geom as geom
    from union_sidewalks;
alter table split_sidewalks add column gid bigserial;
create temporary table rings as
  select ST_ExteriorRing((ST_DumpRings(geom)).geom) as geom, gid
  from split_sidewalks;
with bad as
  (select distinct A.gid from rings as A
  join rings as B
  on A.gid = B.gid
  and not (A.geom = B.geom)
  and ST_Intersects(A.geom, B.geom))
delete from split_sidewalks using bad where split_sidewalks.gid=bad.gid;

-- get medial axis (function returns multiline of segments)
drop table if exists segments;
create temporary table segments as
  (select gid, adacomply, covered, (ST_Dump(ST_ApproximateMedialAxis(geom))).geom as geom
   from split_sidewalks);
delete from segments where ST_Length(geom)=0;

-- join segments into longer strings, now ignoring 'covered'
create temporary table lines as
  select adacomply, (ST_Dump(ST_LineMerge(ST_Collect(geom)))).geom as geom
  from segments
  group by adacomply;
-- delete stubs
delete from lines where ST_Length(geom) < 4;
alter table lines add column id bigserial;
drop table segments;

-- split again into segments, this time without stubs
create table segments as
  with series as
    (select generate_series(1, ST_NPoints(geom)-1) as num, id from lines)
  select lines.id as lineid, num, adacomply, 0.0 as width, ST_Length(geom) as len,
    ST_MakeLine(
      ST_PointN(geom, num),
      ST_PointN(geom, num + 1)) as geom
  from series
  inner join lines
  on series.id = lines.id
  where not (ST_PointN(geom, num) = ST_PointN(geom, num + 1));
alter table segments add column id bigserial;
drop table lines;

-- the earlier join had to drop the reference to the original sidewalk, so this has to be a geometry join
create index on split_sidewalks using GIST(geom);
create index on split_sidewalks (gid);
create index on rings (gid);
update segments
  set width = mindist*2
  from
    (select segments.id as id, min(ST_Distance(segments.geom, rings.geom)) as mindist
     from segments
     inner join split_sidewalks
     on segments.geom && split_sidewalks.geom
     inner join rings
     on split_sidewalks.gid = rings.gid
     group by segments.id) as dists
  where dists.id = segments.id;
delete from segments where width=0;
drop table rings;
drop table split_sidewalks;

create temporary table endpoints as
  select lineid, num, adacomply, width, len, ST_StartPoint(segments.geom) as geom, id
  from segments
--  where num=(select min(sub.num) from segments as sub where sub.lineid=segments.lineid)
  union select lineid, num, adacomply, width, len, ST_EndPoint(segments.geom) as geom, id
  from segments;
--  where num=(select max(sub.num) from segments as sub where sub.lineid=segments.lineid);
create index on endpoints using GIST(geom);
delete from endpoints as a
  using endpoints as b
  where a.geom=b.geom
  and a.id!=b.id;
insert into segments
  select a.lineid, -1, a.adacomply, a.width, a.len, ST_MakeLine(a.geom, ST_Centroid(ST_Collect(a.geom, b.geom)))
  from endpoints as a
  join endpoints as b
  on ST_DWithin(a.geom, b.geom, a.width+b.width+1)
  and a.id!=b.id
  where a.len > 10
  and b.len > 10;
drop table endpoints;

alter table segments add column meterWidth float;
update segments set meterWidth=round(width*0.6096)/2.0;

create temporary table lines as
  select adacomply, meterWidth, ST_Simplify((ST_Dump(ST_LineMerge(ST_Collect(geom)))).geom, 1.0/12.0) as geom
  from segments
  where meterWidth > 0
  group by adacomply, meterWidth;
alter table lines add column gid bigserial;
--drop table segments;
update lines set meterWidth=null where ST_Length(geom)*0.3048 < meterWidth-0.5;

create table lines2 as
  select adacomply, meterWidth, (ST_Dump(ST_LineMerge(ST_Collect(geom)))).geom as geom
  from lines
  group by adacomply, meterWidth;
drop table lines;

