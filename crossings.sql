-- Clean up input
alter table curbRamps drop column lastEditor;
alter table curbRamps drop column lastUpdate;
alter table curbRamps drop column salesforceId;
alter table curbRamps drop column streetSaverId;
alter table curbRamps alter column withinCrosswalk type boolean using (case when withinCrosswalk='Within Crosswalk' then true when withinCrosswalk='Not Within Crosswalk' then false end);
alter table curbRamps alter column midBlock type boolean using (case when midBlock='Yes' then true when midBlock='No' then false end);
update curbRamps set streetNorthSouth=trim(both '. ' from streetNorthSouth);
update curbRamps set streetEastWest=trim(both '. ' from streetEastWest);
update curbRamps set streetNorthSouth=regexp_replace(streetNorthSouth, '  +', ' ');
update curbRamps set streetEastWest=regexp_replace(streetEastWest, '  +', ' ');

alter table curbRamps add column lineToSidewalk geometry(LineString, 2227);
-- Snap to nearest sidewalk edge (outer ring)
create table if not exists ringsGrouped as
  select ST_Transform(ST_ExteriorRing((ST_Dump(ST_UnaryUnion(ST_Collect(geom)))).geom), 2227) as geom from sidewalkArea group by covered;
create index if not exists ringsgrouped_geom_idx on ringsGrouped using GIST(geom);
update curbRamps set lineToSidewalk=ST_ShortestLine(geom, (select geom from ringsGrouped where ringsGrouped.geom && ST_Expand(curbRamps.geom, 30) order by ST_Distance(curbRamps.geom, ringsGrouped.geom) asc limit 1));
update curbRamps set geom=ST_EndPoint(lineToSidewalk) where ST_Length(lineToSidewalk) < 30 and (select count(*) from streets where ST_Intersects(lineToSidewalk, streets.geom))=0;
alter table curbRamps drop column lineToSidewalk;

-- Draw line from sidewalk edge to centerline
drop table if exists linesXform;
create temporary table linesXform as
  select ST_Transform(geom, 2227) as geom, adacomply from lines2;
alter table linesXform add column gid bigserial;
create index on linesXform using GIST(geom);
drop table if exists rampLines;
create table rampLines as
  select ST_ShortestLine(curbRamps.geom, A.geom) as geom, cast ('up' as character varying(4)) as incline, (A.adacomply and curbRamps.adaoverallcompliance='Compliant') as adacomply from curbRamps left outer join linesXform as A on A.geom && ST_Expand(curbRamps.geom, 8) left outer join linesXform as B on B.geom && ST_Expand(curbRamps.geom, 8) and ST_Distance(curbRamps.geom, B.geom) < ST_Distance(curbRamps.geom, A.geom) where B.gid is null;
alter table rampLines add column gid bigserial;
-- Mix up the inclines
update rampLines set incline='down', geom=ST_Reverse(geom) where (gid%2)=0;

-- Get the nearest intersection for each curb
alter table curbRamps add column intersection bigint references intersection;
update curbRamps set intersection=(select objectid from intersection where intersection.geom && ST_Expand(curbRamps.geom, 444.8) order by ST_Distance(curbRamps.geom, intersection.geom) asc limit 1) where midBlock='No';

drop table if exists crossing;
create table crossing (street character varying(80), aid bigint references curbRamps, bid bigint references curbRamps, gid bigserial);

-- Connect curbs with indicated quadrants clockwise
insert into crossing (select A.streetNorthSouth as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='NW' and B.streetQuadrant='NE');
insert into crossing (select A.streetEastWest as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='NE' and B.streetQuadrant='SE');
insert into crossing (select A.streetNorthSouth as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='SE' and B.streetQuadrant='SW');
insert into crossing (select A.streetEastWest as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='SW' and B.streetQuadrant='NW');

-- Connect curbs where we don't know their quadrant but we do know they are on opposite sides of the road
insert into crossing (select A.streetName as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on A.streetName=B.streetName where A.sideOfRoad='Left' and B.sideOfRoad='Right' and (A.streetQuadrant='NA' or B.streetQuadrant='NA') and (A.intersection=B.intersection or (A.midBlock='Yes' and B.midBlock='Yes')));
insert into crossing (select A.streetName as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on (A.streetName || '_R')=B.streetName where (A.streetQuadrant='NA' or B.streetQuadrant='NA') and (A.intersection=B.intersection or (A.midBlock='Yes' and B.midBlock='Yes')));
insert into crossing (with curbRampsSplit as (select objectid, regexp_match(streetName, '(.*) (.B)') as splitName, intersection, streetQuadrant, midBlock from curbRamps) select (A.splitName)[1] as street, A.objectid as aid, B.objectid as bid from curbRampsSplit as A inner join curbRampsSplit as B on (A.splitName)[1]=(B.splitName)[1] and (((A.splitName)[2]='WB' and (B.splitName)[2]='EB') or ((A.splitName)[2]='NB' and (B.splitName)[2]='SB')) where (A.streetQuadrant='NA' or B.streetQuadrant='NA') and (A.intersection=B.intersection or (A.midBlock='Yes' and B.midBlock='Yes')));

-- Lastly, connect curbs on the same side of the road
insert into crossing (select null as street, A.objectid as aid, B.objectid as bid from curbRamps as A inner join curbRamps as B on A.streetName=B.streetName and A.sideOfRoad=B.sideOfRoad where (A.streetQuadrant='NA' or B.streetQuadrant='NA') and A.intersection=B.intersection and A.objectid<B.objectid);

alter table crossing add column withinCrosswalk boolean;
update crossing set withinCrosswalk=case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end from curbRamps as A, curbRamps as B where aid=A.objectid and bid=B.objectid;
alter table crossing add column adaOverallCompliance character varying(20);
update crossing set adaOverallCompliance=case A.adaOverallCompliance when B.adaOverallCompliance then A.adaOverallCompliance else null end from curbRamps as A, curbRamps as B where aid=A.objectid and bid=B.objectid;
alter table crossing add column intersection bigint references intersection;
update crossing set intersection=curbRamps.intersection from curbRamps where aid=curbRamps.objectid;
alter table crossing add column geom geometry(LineString, 2227);
update crossing set geom=ST_MakeLine(A.geom, B.geom) from curbRamps as A, curbRamps as B where aid=A.objectid and bid=B.objectid;

-- Delete unlikely-sized crossings
delete from crossing where ST_Length(geom) > 222.4 or ST_Length(geom) < 4;
-- Delete crossings that cross more than one street (city data only has one line for dual carriageways)
delete from crossing where (select count(*) from streets where ST_Intersects(crossing.geom, streets.geom))>1;
-- Also delete crossings that don't cross any road, if we don't know what road it's supposed to cross
delete from crossing where street is null and (select count(*) from streets where ST_Intersects(crossing.geom, streets.geom))!=1;
-- Delete duplicate crossings where a better one is available
delete from crossing as A using crossing as B where A.street is null and B.street is not null and ST_Intersects(A.geom, B.geom) and not ST_Touches(A.geom, B.geom);
delete from crossing as A using crossing as B where A.street=upper(A.street) and B.street<>upper(B.street) and ST_Intersects(A.geom, B.geom) and not ST_Touches(A.geom, B.geom);
delete from crossing as A using crossing as B where A.gid>B.gid and ST_Equals(A.geom, B.geom);

alter table intersection add column if not exists legs integer;
update intersection set legs=cast (left(intersectionType, 1) as integer) where intersectionType is not null and length(intersectionType) > 0;

-- Delete unmarked crossings from intersections that don't have that many legs
with crossingAndIntersection as (select gid, row_number() over (partition by intersection order by gid asc) as crossingInIntersectionId from crossing where withinCrosswalk is null) delete from crossing using intersection, crossingAndIntersection where withinCrosswalk is null and crossing.intersection=intersection.objectid and crossing.gid=crossingAndIntersection.gid and intersection.legs is not null and crossingInIntersectionId > intersection.legs;
with crossingAndIntersection as (select gid, row_number() over (partition by intersection order by gid asc) as crossingInIntersectionId from crossing where not withinCrosswalk) delete from crossing using intersection, crossingAndIntersection where not withinCrosswalk and crossing.intersection=intersection.objectid and crossing.gid=crossingAndIntersection.gid and intersection.legs is not null and crossingInIntersectionId > intersection.legs;
--with crossingAndIntersection as (select gid, row_number() over (partition by intersection order by gid asc) as crossingInIntersectionId from crossing) delete from crossing using intersection, crossingAndIntersection where crossing.intersection=intersection.objectid and crossing.gid=crossingAndIntersection.gid and intersection.legs is not null and crossingInIntersectionId > intersection.legs;

--delete from crossing as A using crossing as B where A.gid>B.gid and ST_Intersects(A.geom, B.geom) and not ST_Touches(A.geom, B.geom);

