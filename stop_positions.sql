-- shp2pgsql -d -I -D -s 4326 RoadCenterLine_20240312/geo_export_4b3ce19c-a320-4f7a-a384-a43224b9743c RoadCenterLine | psql -b --variable=ON_ERROR_STOP=on
\set ON_ERROR_STOP on

drop table if exists stops;
create table stops (stop_id integer primary key, stop_code varchar(16), stop_name varchar(128), stop_desc varchar(8), stop_lat real, stop_lon real, zone_id integer, stop_url varchar(128), location_type integer, parent_station integer, wheelchair_boarding integer, platform_code varchar(8));
\copy stops from 'gtfs_vta/stops.txt' with (format csv, header true);
select AddGeometryColumn('stops', 'geom', 4326, 'POINT', 2);
update stops set geom=ST_MakePoint(stop_lon, stop_lat);
create index on stops using gist(geom);
alter table stops drop column stop_lat;
alter table stops drop column stop_lon;

drop table if exists stop_positions;
create table stop_positions as (
    select
        stops.stop_code as ref,
        stops.stop_name as name,
        ST_ClosestPoint(RoadCenterLine.geom, stops.geom) as geom,
        row_number() over (partition by stops.stop_code order by ST_Distance(stops.geom, RoadCenterLine.geom)) as rn
    from
        stops
    left join
        RoadCenterLine
    on
        upper(stops.stop_name) like (st_name || ' %')
    where
        stops.stop_name like '%&%' or
        stops.stop_name like '% and %' or
        stops.stop_name like '%@%' or
        stops.stop_name like '% at %' or
        stops.stop_name like '% AT %'
);
delete from stop_positions where rn != 1;
alter table stop_positions drop column rn;

