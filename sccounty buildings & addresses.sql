-- shp2pgsql -d -I -D -s 4326 -m parcel_column_map.txt Parcels_20240313/geo_export_539a39bd-f0c6-402b-9ac7-8a7ca297978a.shp Parcels | psql -b --variable=ON_ERROR_STOP=on
-- shp2pgsql -d -I -D -s 4326 Buildings\ Footprints\ 2D_20240312/geo_export_1076c123-cf33-4f5d-83ac-e72157c09ab4.shp Buildings | psql -b --variable=ON_ERROR_STOP=on

\set ON_ERROR_STOP on

drop table if exists buildings_addresses;
create table buildings_addresses as (
    select
        situs_house_number,
        situs_house_number_suffix,
        situs_street_direction,
        situs_street_name,
        situs_street_type,
        situs_unit_number,
        situs_city_name,
        situs_state_code,
        situs_zip_code,
        base_heigh,
        building_h,
        coalesce(buildings.geom, ST_Centroid(parcels.geom)) as geom,
        row_number() over (partition by parcels.objectid order by ST_Area(buildings.geom) desc) as rn,
        buildings.objectid as buildingid
    from
        parcels
    left join
        buildings
    on
        parcels.geom && buildings.geom and
        ST_Area(ST_Intersection(parcels.geom, buildings.geom)) > 0.9*ST_Area(buildings.geom)
    where
        situs_house_number is not null
);
delete from buildings_addresses where rn != 1;
alter table buildings_addresses drop column rn;

insert into
    buildings_addresses
    (base_heigh, building_h, geom, buildingid)
    select
        buildings.base_heigh,
        buildings.building_h,
        buildings.geom,
        buildings.objectid as buildingid
    from
        buildings
    left join
        buildings_addresses
    on
        buildingid = objectid
    where
        buildingid is null;

alter table buildings_addresses drop column buildingid;

