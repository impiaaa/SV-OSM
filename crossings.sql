update curbRamps set streetNorthSouth=trim(both '. ' from streetNorthSouth);
update curbRamps set streetEastWest=trim(both '. ' from streetEastWest);
update curbRamps set streetNorthSouth=regexp_replace(streetNorthSouth, '  +', ' ');
update curbRamps set streetEastWest=regexp_replace(streetEastWest, '  +', ' ');

create table if not exists ringsGrouped as select row_number() over () as gid, ST_Transform(ST_ExteriorRing((ST_Dump(ST_Union(geom))).geom), 2227) as geom from sidewalkArea;
alter table curbRamps add column lineToSidewalk geometry(LineString, 2227);
update curbRamps set lineToSidewalk=ST_ShortestLine(geom, (select geom from ringsGrouped where ringsGrouped.geom && ST_Expand(curbRamps.geom, 30) order by ST_Distance(curbRamps.geom, ringsGrouped.geom) asc limit 1));
alter table curbRamps add column if not exists castGeom geometry(Point, 2227);
update curbRamps set castGeom=geom;
update curbRamps set castGeom=ST_EndPoint(lineToSidewalk) where ST_Length(lineToSidewalk) < 30 and (select count(*) from streets where ST_Intersects(lineToSidewalk, streets.geom))=0;
alter table curbRamps drop column lineToSidewalk;

-- Get the nearest intersection for each curb
alter table curbRamps add column if not exists intersection bigint references intersection;
update curbRamps set intersection=(select objectid from intersection where intersection.geom && ST_Expand(curbRamps.geom, 444.8) order by ST_Distance(curbRamps.geom, intersection.geom) asc limit 1) where midBlock='No';

drop table crossing;
create table crossing (street character varying(80), withincrosswalk character varying(20), intersection bigint references intersection, geom geometry(LineString, 2227), gid bigserial);

-- Connect curbs with indicated quadrants clockwise
insert into crossing (select A.streetNorthSouth as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='NW' and B.streetQuadrant='NE');
insert into crossing (select A.streetEastWest as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='NE' and B.streetQuadrant='SE');
insert into crossing (select A.streetNorthSouth as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='SE' and B.streetQuadrant='SW');
insert into crossing (select A.streetEastWest as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on A.streetNorthSouth=B.streetNorthSouth and A.streetEastWest=B.streetEastWest where A.streetQuadrant='SW' and B.streetQuadrant='NW');

-- Connect curbs where we don't know their quadrant but we do know they are on opposite sides of the road
insert into crossing (select A.streetName as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on A.streetName=B.streetName where A.sideOfRoad='Left' and B.sideOfRoad='Right' and (A.streetQuadrant='NA' or B.streetQuadrant='NA') and (A.intersection=B.intersection or (A.midBlock='Yes' and B.midBlock='Yes')));
insert into crossing (select A.streetName as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on (A.streetName || '_R')=B.streetName where (A.streetQuadrant='NA' or B.streetQuadrant='NA') and (A.intersection=B.intersection or (A.midBlock='Yes' and B.midBlock='Yes')));
insert into crossing (with curbRampsSplit as (select regexp_match(streetName, '(.*) (.B)') as splitName, withinCrosswalk, intersection, castGeom, streetQuadrant, midBlock from curbRamps) select (A.splitName)[1] as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRampsSplit as A inner join curbRampsSplit as B on (A.splitName)[1]=(B.splitName)[1] and (((A.splitName)[2]='WB' and (B.splitName)[2]='EB') or ((A.splitName)[2]='NB' and (B.splitName)[2]='SB')) where (A.streetQuadrant='NA' or B.streetQuadrant='NA') and (A.intersection=B.intersection or (A.midBlock='Yes' and B.midBlock='Yes')));

-- Lastly, connect curbs on the same side of the road
insert into crossing (select null as street, case A.withinCrosswalk when B.withinCrosswalk then A.withinCrosswalk else null end as withinCrosswalk, A.intersection as intersection, ST_MakeLine(A.castGeom, B.castGeom) as geom from curbRamps as A inner join curbRamps as B on A.streetName=B.streetName and A.sideOfRoad=B.sideOfRoad where (A.streetQuadrant='NA' or B.streetQuadrant='NA') and A.intersection=B.intersection and A.objectid<B.objectid);

delete from crossing where ST_Length(geom) > 222.4 or ST_Length(geom) < 4;
delete from crossing where (select count(*) from streets where ST_Intersects(crossing.geom, streets.geom))>1;
delete from crossing where street is null and (select count(*) from streets where ST_Intersects(crossing.geom, streets.geom))!=1;
delete from crossing as A using crossing as B where A.street is null and B.street is not null and ST_Intersects(A.geom, B.geom) and not ST_Touches(A.geom, B.geom);
delete from crossing as A using crossing as B where A.street=upper(A.street) and B.street<>upper(B.street) and ST_Intersects(A.geom, B.geom) and not ST_Touches(A.geom, B.geom);
delete from crossing as A using crossing as B where A.gid>B.gid and ST_Equals(A.geom, B.geom);

alter table intersection add column if not exists legs integer;
update intersection set legs=cast (left(intersectionType, 1) as integer) where intersectionType is not null and length(intersectionType) > 0;

with crossingAndIntersection as (select gid, row_number() over (partition by intersection order by gid asc) as crossingInIntersectionId from crossing where withinCrosswalk is null) delete from crossing using intersection, crossingAndIntersection where withinCrosswalk is null and crossing.intersection=intersection.objectid and crossing.gid=crossingAndIntersection.gid and intersection.legs is not null and crossingInIntersectionId > intersection.legs;
with crossingAndIntersection as (select gid, row_number() over (partition by intersection order by gid asc) as crossingInIntersectionId from crossing where withinCrosswalk='Not Within Crosswalk') delete from crossing using intersection, crossingAndIntersection where withinCrosswalk='Not Within Crosswalk' and crossing.intersection=intersection.objectid and crossing.gid=crossingAndIntersection.gid and intersection.legs is not null and crossingInIntersectionId > intersection.legs;
--with crossingAndIntersection as (select gid, row_number() over (partition by intersection order by gid asc) as crossingInIntersectionId from crossing) delete from crossing using intersection, crossingAndIntersection where crossing.intersection=intersection.objectid and crossing.gid=crossingAndIntersection.gid and intersection.legs is not null and crossingInIntersectionId > intersection.legs;

--delete from crossing as A using crossing as B where A.gid>B.gid and ST_Intersects(A.geom, B.geom) and not ST_Touches(A.geom, B.geom);

