\set ON_ERROR_STOP on

\set CENTROID_MAX_DIST 100
\set FEET_TO_METERS 0.3048
\set MAX_HAUSDORFF_SIMILARITY 61
\set MIN_OVERLAP_SIMILARITY 0.1

-- Functions

create or replace function
    TranslateByPoint(
        geom geometry,
        point geometry(Point)
    )
returns
    geometry
language SQL
immutable
returns null on null input
return
    ST_Translate(geom, ST_X(point), ST_Y(point));

create or replace function
    adjustment_state(
        state geometry(Point)[],
        next geometry
    )
returns
    geometry(Point)[]
language
    SQL
strict
as $$
with
    city_centroids
as (
    select
        ST_Centroid(next) as geom
),
    diffs
as (
    select
        ST_X(county_buildings.centroid) - ST_X(city_centroids.geom) as x,
        ST_Y(county_buildings.centroid) - ST_Y(city_centroids.geom) as y,
        row_number() over (partition by city_centroids.* order by county_buildings.centroid <-> city_centroids.geom) as rn
    from
        city_centroids
    left join
        county_buildings
    on
        ST_DWithin(county_buildings.centroid, city_centroids.geom, :CENTROID_MAX_DIST)
)
select
    array_append($1, ST_Point(x, y))
from
    diffs
where
    rn = 1
$$;

create or replace function
    adjustment_final(
        state geometry(Point)[]
    )
returns
    geometry
language
    SQL
strict
as $$
with
    points
as (
    select ST_X(geom) as x, ST_Y(geom) as y from unnest(state) as geom
)
select
    ST_Point(
        percentile_cont(0.5) within group (order by x),
        percentile_cont(0.5) within group (order by y)
    )
from
    points
$$;

-- calculates the median difference between the closest county points to city points
-- i.e., for each city building in the aggregate, take the centroid, find the closest county
-- building centroid, and take the difference in coordinates, then take the median of those
-- differences.
create or replace aggregate
    adjustment(geometry)
(
    sfunc = adjustment_state,
    stype = geometry(Point)[],
    initcond = '{}',
    finalfunc = adjustment_final
);

-- Clean up input data

-- Unify all geometry to EPSG:2227 (NAD83 California zone 3)
-- (better for geometry processing to use a local projection instead of WGS84)
alter table
    county_buildings
add if not exists
    loc_geom
    geometry('POLYGON', 2227);
update
    county_buildings
set
    loc_geom=ST_Transform(geom, 2227)
where
    loc_geom is null;
create index if not exists
    county_loc_geom_index
on
    county_buildings
using
    gist(loc_geom);

-- Pre-calculate the centroid of every building, for matching to city buildings
alter table
    county_buildings
add if not exists
    centroid
    geometry('POINT', 2227);
update
    county_buildings
set
    centroid=ST_Centroid(loc_geom)
where
    centroid is null;
create index if not exists
    county_centroid_index
on
    county_buildings
using
    gist(centroid);
create index if not exists
    county_centroid_expand_index
on
    county_buildings
using
    gist(ST_Expand(centroid, :CENTROID_MAX_DIST));

-- Create a table to hold input data from all cities
drop table if exists
    city_buildings;
create table
    city_buildings
    (
        gid serial primary key,
        --addr_city varchar,
        --addr_full varchar,
        building varchar not null default 'yes',
        building_levels integer,
        ele real,
        flats integer,
        height real,
        name varchar,
        start_date date,
        geom geometry('MULTIPOLYGON', 2227),
        data_date timestamp
    );

-- Cupertino input data
insert into
    city_buildings
    (building, ele, height, building_levels, start_date, geom, data_date)
select
    case
        when level_desc='Canopy' then 'roof'
        when level_desc='Canopy Structure' then 'roof'
        when level_desc='Shed' then 'shed'
        else 'yes'
    end as building,
    bldg_low::real * :FEET_TO_METERS as ele,
    bldg_heigh * :FEET_TO_METERS as height,
    floornumbe as building_levels,
    year_built as start_date,
    TranslateByPoint(ST_Transform(geom, 2227), adjustment(ST_Transform(geom, 2227)) over ()) as geom,
    coalesce(created_da, last_edi_1, '2011-01-01 00:00:00'::timestamp) as data_date
from
    cupertino_buildings
where
    (
        level_desc is null
    or
        level_desc <> 'Swimming Pool'
    )
--and
--    geom && ST_MakeBox2D(ST_Point(-122.03234334, 37.31612497), ST_Point(-122.02320717, 37.32295951))
;

-- Gilroy input data
insert into
    city_buildings
    (building, name, flats, data_date, geom)
select
    case
        when BldgSubtype='APARTMENT' then 'apartments'
        when BldgSubtype='CHURCH' then 'church'
        when BldgSubtype='CONDOMINIUM' then 'apartments'
        when BldgSubtype='FIRE' then 'fire_station'
        when BldgSubtype='GOVT_FAC' then 'government'
        when BldgSubtype='MUSEUM' then 'museum'
        when BldgSubtype='OFFICE' then 'office'
        when BldgSubtype='SCHOOL' then 'school'
        when BldgSubtype='UTILITY' then 'service'
        when BldgType='COMMERCIAL' then 'retail'
        when BldgType='INDUSTRIAL' then 'industrial'
        when BldgType='PUBLIC_FAC' then 'civic'
        when BldgType='RESIDENTIAL' then 'residential'
        else 'yes'
    end as building,
    BldgName as name,
    --Address as addr_full,
    NumberOfUnits as flats,
    --City as addr_city,
    coalesce(CreateDate, RevDate, '2023-08-01 00:00:00'::timestamp) as data_date,
    TranslateByPoint(geom, adjustment(geom) over ()) as geom
from
    gilroy_buildings
--where
--    geom && ST_MakeBox2D(ST_Point(6248102.43, 1830062.04), ST_Point(6249915.61, 1831887.91))
;

-- Los Gatos input data
insert into
    city_buildings
    (geom, data_date)
select
    TranslateByPoint(ST_Transform(geom, 2227), adjustment(ST_Transform(geom, 2227)) over ()) as geom,
    '2014-08-13 00:00:00'::timestamp as data_date
from
    los_gatos_buildings;

-- Milpitas input data
insert into
    city_buildings
    (geom, data_date)
select
    TranslateByPoint(ST_Transform(geom, 2227), adjustment(ST_Transform(geom, 2227)) over ()) as geom,
    coalesce(ts, '2019-04-04 00:00:00'::timestamp) as data_date
from
    milpitas_buildings
where
    (
        descriptio is null
    or
        descriptio <> 'Pool'
    )
--and
--    geom && ST_MakeBox2D(ST_Point(-121.88699722, 37.43042064), ST_Point(-121.88102339, 37.43545500))
;

-- Mountain View input data
insert into
    city_buildings
    (building_levels, height, name, building, geom, data_date)
select
    numstories as building_levels,
    bldgheight*:FEET_TO_METERS as height,
    name as name,
    case
        --when type='Complex' then 'civic'
        when type='Entertainment' then 'commercial'
        --when type='Facility' then 'government'
        when type='Gate House' then 'guardhouse'
        --when type='Historic Site' then 'house'
        when type='Hospital' then 'hospital'
        --when type='Medical Center' then 'public'
        --when type='Point of Interest' then 'military'
        when type='Public Safety' then 'fire_station'
        when type='Pump Station' then 'service'
        when type='School' then 'school'
        --when type='Senior Day Care' then 'civic'
        when type='TOWNHOME' then 'terrace'
        when type='TRASH ENCLOSURE' then 'shed'
        else 'yes'
    end as building,
    TranslateByPoint(ST_Transform(ST_Force2D(geom), 2227), adjustment(ST_Transform(ST_Force2D(geom), 2227)) over ()) as geom,
    coalesce(created_da, last_edi_1, '2017-07-31 00:00:00'::timestamp) as data_date
from
    mountain_view_buildings
--where
--    geom && ST_MakeBox2D(ST_Point(6102224.83, 1967959.21), ST_Point(6104152.70, 1969396.57))
;

-- Palo Alto input data
insert into
    city_buildings
    (name, geom, data_date)
select
    case
        when name='unk' then NULL
        else initcap(name)
    end as name,
    TranslateByPoint(geom, adjustment(geom) over ()) as geom,
    coalesce(createddat, modifiedda, '2022-07-07 00:00:00'::timestamp) as data_date
from
    palo_alto_buildings
--where
--    geom && ST_MakeBox2D(ST_Point(6079340.06, 1986794.79), ST_Point(6081101.01, 1988555.08))
;

-- Santa Clara (city) input data
insert into
    city_buildings
    (ele, height, geom, data_date)
select
    baseelev * :FEET_TO_METERS as ele,
    bldgheight * :FEET_TO_METERS as height,
    TranslateByPoint(ST_Transform(ST_Force2D(geom), 2227), adjustment(ST_Transform(ST_Force2D(geom), 2227)) over ()) as geom,
    '2015-03-01 00:00:00'::timestamp as data_date
from
    santa_clara_buildings
--where
--    geom && ST_MakeBox2D(ST_Point(6133736.57, 1943509.07), ST_Point(6136734.27, 1945938.40))
;

-- Sunnyvale input data
insert into
    city_buildings
    (height, ele, building, building_levels, geom, data_date)
select
    bldg_heigh * :FEET_TO_METERS as height,
    bldg_low::real * :FEET_TO_METERS as ele,
    case
        when bldg_type='Dwelling' then 'residential'
        when bldg_type='Parking' then 'garages'
        else 'yes'
    end as building,
    --initcap(address) as addr_full,
    story as building_levels,
    TranslateByPoint(ST_Transform(geom, 2227), adjustment(ST_Transform(geom, 2227)) over ()) as geom,
    '2021-04-05 00:00:00'::timestamp as data_date
from
    sunnyvale_buildings
--where
--    geom && ST_MakeBox2D(ST_Point(-122.02992506, 37.36562509), ST_Point(-122.02384854, 37.37157382))
;

update
    city_buildings
set
    geom=ST_MakeValid(geom, 'method=structure')
where
not
    ST_IsValid(geom);

create index if not exists
    city_geom_index
on
    city_buildings
using
    gist(geom);

-- Conflation

create temporary table
    county_intersections
as (
    select
        county_buildings.*,
        count(city_buildings.*) as intersection_count,
        --ST_Area(ST_SymmetricDifference(county_buildings.loc_geom, ST_Union(city_buildings.geom)))/ST_Area(county_buildings.loc_geom) < 1.048 as similar_shape
        ST_HausdorffDistance(ST_ConvexHull(county_buildings.loc_geom), ST_ConvexHull(ST_Collect(city_buildings.geom))) < :MAX_HAUSDORFF_SIMILARITY as similar_shape
    from
        county_buildings
    left join
        city_buildings
    on
        county_buildings.loc_geom && city_buildings.geom
    and
        ST_Intersects(county_buildings.loc_geom, city_buildings.geom)
    and
        ST_Area(ST_Intersection(county_buildings.loc_geom, city_buildings.geom)) > :MIN_OVERLAP_SIMILARITY * least(ST_Area(county_buildings.loc_geom), ST_Area(city_buildings.geom))
    group by
        county_buildings.gid, county_buildings.geom
);
create index on
    county_intersections
using
    gist(loc_geom);
analyze county_intersections;

drop table if exists import_buildings;
with
    intersections
as (
    select distinct
        city_buildings.*,
        min(county_intersections.base_heigh) as base_heigh,
        max(county_intersections.building_h) as building_h,
        count(county_intersections.*) as intersection_count,
        --ST_Area(ST_SymmetricDifference(city_buildings.geom, ST_Union(county_intersections.loc_geom)))/ST_Area(city_buildings.geom) < 0.25 as similar_shape,
        ST_HausdorffDistance(ST_ConvexHull(city_buildings.geom), ST_ConvexHull(ST_Collect(county_intersections.loc_geom))) < :MAX_HAUSDORFF_SIMILARITY as similar_shape,
        city_buildings.data_date > '2020-01-01 00:00:00'::timestamp as newer,
        ST_NPoints(city_buildings.geom) > sum(ST_NPoints(county_intersections.loc_geom)) as higher_detail,
        sum(county_intersections.intersection_count) as other_intersection_count,
        bool_and(county_intersections.similar_shape) as other_similar_shape
    from
        city_buildings
    left join
        county_intersections
    on
        city_buildings.geom && county_intersections.loc_geom
    and
        ST_Intersects(city_buildings.geom, county_intersections.loc_geom)
    and
        ST_Area(ST_Intersection(city_buildings.geom, county_intersections.loc_geom)) > :MIN_OVERLAP_SIMILARITY * least(ST_Area(city_buildings.geom), ST_Area(county_intersections.loc_geom))
    group by
        city_buildings.gid, city_buildings.geom, city_buildings.data_date
)
select distinct
    --addr_city,
    --addr_full,
    building,
    building_levels,
    coalesce(ele, base_heigh*:FEET_TO_METERS) as ele,
    flats,
    coalesce(height, building_h*:FEET_TO_METERS) as height,
    name,
    start_date,
    -- Offset measured by manually aligning survey point AA1873 to ESRI imagery, then manually
    -- aligning the nearby county building outlines to the imagery
    ST_Translate(ST_Transform(geom, 4326), 0.0000049, -0.0000052)
into
    import_buildings
from
    intersections
where
    intersections.intersection_count = 0
    or
    (
        intersections.intersection_count = 1
        and
        (
            (
                other_intersection_count = 1
                and
                (
/*
                    (
                        intersections.similar_shape
                        and
                        intersections.higher_detail
                    )
                    or
                    (
                        not intersections.similar_shape
                        and
                        intersections.newer
                    )
*/
                    intersections.similar_shape
                    or
                    intersections.newer
                )
            )
            or
            (
                other_intersection_count > 1
                and
                (
                    other_similar_shape
                    or
                    (
                        not intersections.similar_shape
                        and
                        intersections.newer
                    )
                )
            )
        )
    )
    or
    (
        intersections.intersection_count > 1
        and
        (
            (
                other_intersection_count = 1
                and
                not intersections.similar_shape
                and
                intersections.newer
            )
            or
            (
                other_intersection_count > 1
                and
                intersections.newer
            )
        )
    );

