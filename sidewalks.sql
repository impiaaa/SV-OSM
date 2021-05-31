alter table SidewalkArea drop column width;
alter table SidewalkArea drop column area;
alter table SidewalkArea alter column adacomply type boolean using (adacomply = 'Yes');
alter table SidewalkArea alter column covered type boolean using (covered = 'Yes');

-- union sidewalk geometries, then split again
create temporary table merged_sidewalks as
  with union_sidewalks as
    (select ST_UnaryUnion(ST_Collect(ST_RemoveRepeatedPoints(geom, 0.25))) as geom
     from SidewalkArea
     group by covered)
    select (ST_Dump(geom)).geom as geom
    from union_sidewalks;
alter table merged_sidewalks add column gid bigserial;
create temporary table merged_rings as
  select ST_ExteriorRing((ST_DumpRings(geom)).geom) as geom, gid
  from merged_sidewalks;
with bad as
  (select distinct A.gid from merged_rings as A
   join merged_rings as B
   on A.gid = B.gid
   and not (A.geom = B.geom)
   and ST_Intersects(A.geom, B.geom))
  delete from merged_sidewalks using bad where merged_sidewalks.gid=bad.gid;

-- get medial axis (function returns multiline of segments)
create temporary table segments as
  (select gid, 0.0 as width, (ST_Dump(ST_ApproximateMedialAxis(geom))).geom as geom
   from merged_sidewalks);
delete from segments where ST_Length(geom)=0;

-- the earlier join had to drop the reference to the original sidewalk, so this has to be a geometry join
create index on merged_sidewalks using GIST(geom);
create index on merged_sidewalks (gid);
create index on merged_rings (gid);
update segments
  set width = mindist*2
  from
    (select segments.gid as gid, min(ST_Distance(segments.geom, merged_rings.geom)) as mindist
     from segments
     inner join merged_sidewalks
     on segments.geom && merged_sidewalks.geom
     inner join merged_rings
     on merged_sidewalks.gid = merged_rings.gid
     group by segments.gid) as dists
  where dists.gid = segments.gid;
delete from segments where width=0;
drop table merged_rings;
drop table merged_sidewalks;

alter table segments add column meterWidth float;
update segments set meterWidth=round(width*0.6096)/2.0;

create table split_segments as
  select null as adacomply, meterWidth, (ST_Dump(ST_Split(segments.geom, SidewalkArea.geom))).geom as geom
  from segments
  join SidewalkArea
  on ST_Crosses(segments.geom, SidewalkArea.geom);
update split_segments
  set adacomply = SidewalkArea.adacomply
  from SidewalkArea
  where ST_Contains(SidewalkArea.geom, split_segments.geom);

create temporary table lines as
  select adacomply, meterWidth, (ST_Dump(ST_LineMerge(ST_Collect(geom)))).geom as geom
  from split_segments
  where meterWidth > 0
  group by adacomply, meterWidth;
alter table lines add column gid bigserial;
-- Not useful to have tiny segments just because of differing widths
update lines set meterWidth=null where ST_Length(geom)*0.3048 < meterWidth;

-- Re-join with tiny segments combined
drop table if exists lines2;
create table lines2 as
  select adacomply, meterWidth, ST_Simplify((ST_Dump(ST_LineMerge(ST_Collect(geom)))).geom, 1.0) as geom
  from lines
  group by adacomply, meterWidth;

