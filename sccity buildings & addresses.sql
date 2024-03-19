\set ON_ERROR_STOP on

-- Select all possible (address, building, parcel) pairs
drop table if exists buildings_addresses;
create table
    buildings_addresses
as
    select
        addresses.gid as address_gid,
        building.gid as building_gid,
        land_parcels.gid as parcel_gid,
        row_number() over (partition by land_parcels.gid order by ST_Distance(addresses.geom, building.geom)) as parcel_row,
        cscstreet, addrnum, addrunit, addrcity, addrzip5,
        yearbuilt,
        baseelev, bldgheight, floorcount, eaveheight, roofdir,
        ST_Force2D(building.geom)::geometry(Geometry, 6420) as geom
    from
        addresses
    inner join
        land_parcels
    on
        addresses.geom && land_parcels.geom
    and
        ST_Within(addresses.geom, land_parcels.geom)
    inner join
        building
    on
        building.geom && land_parcels.geom
    and
        ST_Area(ST_Intersection(building.geom, land_parcels.geom)) > 0.9*ST_Area(building.geom);

-- Skip addresses that are in more than one parcel
delete from
    buildings_addresses
where
    address_gid in (
        select
            address_gid
        from
            buildings_addresses
        group by
            address_gid, building_gid
        having
            count(distinct parcel_gid) > 1
    );

-- Skip buildings that match more than one address
delete from
    buildings_addresses
where
    building_gid in (
        select
            building_gid
        from
            buildings_addresses
        group by
            building_gid
        having
            count(distinct address_gid) > 1
    );

-- Select only the closest building to each address
delete from
    buildings_addresses
where
    parcel_row != 1;

-- Reinsert skipped buildings, but without an address
insert into
    buildings_addresses
    (
        building_gid,
        parcel_row,
        yearbuilt,
        baseelev, bldgheight, floorcount, eaveheight, roofdir,
        geom
    )
select
    building.gid as building_gid,
    row_number() over (partition by building.gid order by ST_Area(ST_Intersection(building.geom, land_parcels.geom)) desc) as parcel_row,
    yearbuilt,
    baseelev, bldgheight, floorcount, eaveheight, roofdir,
    ST_Force2D(building.geom) as geom
from
    building
left join
    land_parcels
on
    building.geom && land_parcels.geom
where
    building.gid
not in
    (
        select
            building_gid
        from
            buildings_addresses
    );
delete from
    buildings_addresses
where
    parcel_row != 1;

-- Reinsert skipped addresses, as points without a building
insert into
    buildings_addresses
    (
        address_gid,
        cscstreet, addrnum, addrunit, addrcity, addrzip5,
        geom
    )
select
    gid as address_gid,
    cscstreet, addrnum, addrunit, addrcity, addrzip5,
    ST_Force2D(geom) as geom
from
    addresses
where
    addresses.gid
not in
    (
        select
            address_gid
        from
            buildings_addresses
        where
            address_gid
        is not null
    );

