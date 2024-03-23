-- shp2pgsql -d -I -D -G -s 4326 -g geog RoadCenterLine_20240312/geo_export_4b3ce19c-a320-4f7a-a384-a43224b9743c RoadCenterLine | psql -b --variable=ON_ERROR_STOP=on
\set ON_ERROR_STOP on

drop table if exists stops;
create table stops (
    stop_id integer primary key,
    stop_code varchar(5),
    stop_name varchar(42),
    stop_desc varchar(1),
    stop_lat real,
    stop_lon real,
    zone_id integer,
    stop_url varchar(1),
    location_type integer,
    parent_station integer,
    wheelchair_boarding integer,
    platform_code varchar(1)
);
\copy stops from 'gtfs_vta/stops.txt' with (format csv, header true);
alter table stops add column geog geography(POINT, 4326);
update stops set geog=ST_MakePoint(stop_lon, stop_lat);
alter table stops drop column stop_lat;
alter table stops drop column stop_lon;
create index on stops using gist(geog);

drop table if exists stop_positions;
create table stop_positions as (
    select
        stops.stop_code as ref,
        stops.stop_name as name,
        \if `expr $(shp2pgsql -? | grep RELEASE: | grep -o '[0-9]\.[0-9]') '>=' 3.4`
            ST_ClosestPoint(RoadCenterLine.geog, stops.geog)
        \else
            ST_Transform(ST_ClosestPoint(ST_Transform(RoadCenterLine.geog::geometry, 2227), ST_Transform(stops.geog::geometry, 2227)), 4326)
        \endif
        as geog,
        row_number() over (partition by stops.stop_code order by ST_Distance(stops.geog, RoadCenterLine.geog)) as rn
    from
        stops
    left join
        RoadCenterLine
    on
        upper(stops.stop_name) like (replace(st_name, ' ', '_') || ' %') or
        (st_name = 'EL CAMINO REAL' and stops.stop_name like 'El Camino & %') or
        (st_name = 'ARROYO' and stops.stop_name like 'Camino Arroyo & %')
    where
        stops.stop_name like '%&%' or
        stops.stop_name like '% and %' or
        stops.stop_name like '%@%' or
        stops.stop_name like '% at %' or
        stops.stop_name like '% AT %'
);
delete from stop_positions where rn != 1;
alter table stop_positions drop column rn;

