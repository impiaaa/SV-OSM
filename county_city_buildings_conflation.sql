-- TODO:
-- Intersections should be "significant" to consider (ratio between intersection area and...?)

\set ON_ERROR_STOP on

alter table
    county_buildings
add if not exists
    loc_geom
    geometry('MULTIPOLYGON', 2227);
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

drop table if exists
    city_buildings;
create table
    city_buildings
    (
        gid serial primary key,
        addr_city varchar,
        addr_full varchar,
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

with
    gilroy_centroids
as (
    select
        ST_Centroid(geom) as geom
    from
        gilroy_buildings
),
    diffs
as (
    select
        ST_X(county_buildings.centroid) - ST_X(gilroy_centroids.geom) as x,
        ST_Y(county_buildings.centroid) - ST_Y(gilroy_centroids.geom) as y,
        row_number() over (partition by gilroy_centroids.* order by ST_Distance(county_buildings.centroid, gilroy_centroids.geom)) as rn
    from
        gilroy_centroids
    left join
        county_buildings
    on
        ST_Distance(county_buildings.centroid, gilroy_centroids.geom) < 100
),
    adjustment
as (
    select
        percentile_cont(0.5) within group (order by x) as x,
        percentile_cont(0.5) within group (order by y) as y
    from
        diffs
    where
        rn = 1
)
insert into
    city_buildings
    (building, name, addr_full, flats, addr_city, data_date, geom)
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
    Address as addr_full,
    NumberOfUnits as flats,
    City as addr_city,
    coalesce(CreateDate, RevDate, '2023-08-01 00:00:00'::timestamp) as data_date,
    ST_Translate(geom, adjustment.x, adjustment.y) as geom
from
    gilroy_buildings
left join
    adjustment
on
    1 = 1;

create index if not exists
    city_geom_index
on
    city_buildings
using
    gist(geom);

/*
with
    county_intersections
as (
    select distinct
        county_buildings.*,
        count(city_buildings.*) as intersection_count,
        ST_Area(ST_SymmetricDifference(county_buildings.loc_geom, ST_Union(city_buildings.geom)))/ST_Area(county_buildings.loc_geom) as similarity
    from
        county_buildings
    left join
        city_buildings
    on
        county_buildings.loc_geom && city_buildings.geom and
        ST_Intersects(county_buildings.loc_geom, city_buildings.geom)
    group by
        county_buildings.gid, county_buildings.geom
)
select distinct
    city_buildings.*,
    min(county_intersections.base_heigh) as base_heigh,
    max(county_intersections.building_h) as building_h,
    count(county_intersections.*) as intersection_count,
    ST_Area(ST_SymmetricDifference(city_buildings.geom, ST_Union(county_intersections.loc_geom)))/ST_Area(city_buildings.geom) as similarity,
    city_buildings.data_date > '2020-01-01 00:00:00'::timestamp as newer,
    ST_NPoints(city_buildings.geom) - sum(ST_NPoints(county_intersections.loc_geom)) as detail_diff,
    sum(county_intersections.intersection_count) as other_intersection_count,
    avg(county_intersections.similarity) as other_similarity
into
    city_building_metrics
from
    city_buildings
left join
    county_intersections
on
    city_buildings.geom && county_intersections.loc_geom and
    ST_Intersects(city_buildings.geom, county_intersections.loc_geom)
group by
    city_buildings.gid, city_buildings.geom, city_buildings.data_date;
*/

drop table if exists import_buildings;
with
    county_intersections
as (
    select distinct
        county_buildings.*,
        count(city_buildings.*) as intersection_count,
        --ST_Area(ST_SymmetricDifference(county_buildings.loc_geom, ST_Union(city_buildings.geom)))/ST_Area(county_buildings.loc_geom) < 0.25 as similar_shape
        ST_HausdorffDistance(county_buildings.loc_geom, ST_Union(city_buildings.geom)) < 15 as similar_shape
    from
        county_buildings
    left join
        city_buildings
    on
        county_buildings.loc_geom && city_buildings.geom and
        ST_Intersects(county_buildings.loc_geom, city_buildings.geom)
    group by
        county_buildings.gid, county_buildings.geom
),
    intersections
as (
    select distinct
        city_buildings.*,
        min(county_intersections.base_heigh) as base_heigh,
        max(county_intersections.building_h) as building_h,
        count(county_intersections.*) as intersection_count,
        --ST_Area(ST_SymmetricDifference(city_buildings.geom, ST_Union(county_intersections.loc_geom)))/ST_Area(city_buildings.geom) < 0.25 as similar_shape,
        ST_HausdorffDistance(city_buildings.geom, ST_Union(county_intersections.loc_geom)) < 15 as similar_shape,
        city_buildings.data_date > '2020-01-01 00:00:00'::timestamp as newer,
        ST_NPoints(city_buildings.geom) > sum(ST_NPoints(county_intersections.loc_geom)) as higher_detail,
        sum(county_intersections.intersection_count) as other_intersection_count,
        bool_and(county_intersections.similar_shape) as other_similar_shape
    from
        city_buildings
    left join
        county_intersections
    on
        city_buildings.geom && county_intersections.loc_geom and
        ST_Intersects(city_buildings.geom, county_intersections.loc_geom)
    group by
        city_buildings.gid, city_buildings.geom, city_buildings.data_date
)
select distinct
    addr_city,
    addr_full,
    building,
    building_levels,
    coalesce(ele, base_heigh*0.3048) as ele,
    flats,
    coalesce(height, building_h*0.3048) as height,
    name,
    start_date,
    geom
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
