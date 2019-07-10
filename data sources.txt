# Silicon Valley area geodata
A survey of data available from certain government and related entities for candidates to import into OpenStreetMap.

## Tools

### [ogr2osm](https://github.com/impiaaa/ogr2osm)
A command-line tool for converting many different geospacial data files into OSM files. Translation scripts to use with ogr2osm are included under the translations directory. My fork includes some minor changes that my scripts take advantage of, but they should mostly work with [pnorman's version](https://github.com/pnorman/ogr2osm) as well.

### [GO_Sync](https://github.com/CUTR-at-USF/gtfs-osm-sync)
It's supposed to be able to copy GTFS data into OSM, but I had some trouble with it. It doesn't seem to correctly match stops with ref=, and it does not handle trip/route distinction.

### JOSM
Here are some plugins I found useful during testing:
* conflation
* contourmerge
* kendzi3d
* measurement
* pt_assistant
* public_transport
* reltoolbox
* scripting  
  This one I used a lot to manipulate data after it had been imported. Scripts for it are in the scripts directory. The API is a bit clunky though so they could be rewritten for a different system.
* utilsplugin2
* waydownloader

## [SCVTA open data site](http://data.vta.org/search?sort=name)
### Open Data Portal Terms of Use
Very permissive terms!

### BART Webservice
`railway=*`  
all already mapped, limited additional information
* SCC BART Stops
* BART Phase 1
* BART Phase 2

### BikePedCollisions
probably not useful
* Bicycle Collision 2008-2012
* Pedestrian Collisions 2008-2012

### CountywideBikePlan2018 WebMap
* Point Across Barrier Connections
* Line Across Barrier Connections
* Cross County Bikeway Corridors  
  could use to add/confirm bike lanes, but I think there was already an import for that
* Priority Corridors  
  same as above? maybe existing, not proposed

### General Plan Land Use Webservice
`landuse=*`  
also seems to work around streets.  
would additionally need collation for all the cities
* Campbell GPLU
* Cupertino GPLU
* Gilroy GPLU
* Los Gatos Zoning
* Milpitas GPLU
* Monte Sereno GPLU
* Morgan Hill GPLU
* Mountain View GPLU
* Palo Alto GPLU
* San Jose GPLU
* Santa Clara GPLU 2025-2035
* Sunnyvale GPLU
* SC County GPLU
* ABAG Planned Land Use 2006

### HighwayTOS
* Ramp Meter Construction  
  combine with below
* Ramp Meters  
  rampmeters.py  
  `traffic_signals=ramp_meter` - 708  
  very inaccurate placement
* Existing CCTV  
  cctv.py  
  `surveillance:zone=traffic` - 8131
* CCTV - No Equipment  
  combine with above (proposed)
* PeMS 2012 SCL
* Freeway HOV Lanes  
  `hov:lanes=*` - 4249
* Expressway HOV Lanes  
  combine with above
* Existing Express Lanes  
  only 2, on 237 and 680. find out what they are - thought fasttrak was more commonplace

### LOSwebmap
* CMP Intersections 2016
* LOS Mix AM 2016
* LOS Mix PM 2016
* LOS HOV AM 2016
* LOS HOV PM 2016
* CMP Intersections 2014
* LOS Expressways 2014
* LOS Mix AM 2013
* LOS Mix PM 2013
* CMP Intersections 2012

### PedAccessPlan
probably not useful
* Project Locations
* Focus Areas

### PlanningWebService
probably not useful
* Growth Areas
* Urban Villages
* Cores, Corridors, and Station Areas
* Priority Development Areas

### Bike Paths Lanes Routes
already imported?

### Bus 2018
vta.py, vta.js  
`route=bus`  
same as gtfs, would likely need transition to PTv2  
algorithm to determine routes for paths is complex. works… mostly. doesn't split ways.  
do NOT use to detect stops on route  

### Bus Stop Inventory
vta.py, vta.js  
`highway=bus_stop`  
lots of really useful info, not all has (direct) translation  
could be a big conflation effort  
less necessary to move to PTv2  
if v2, not obvious if it should be stop position or platform (placement accuracy)  

### CaltrainPnR
### GTFS/VTA GTFS Data File
`route=bus`  
lots of good information, but distinguishes routes from trips, and neither the current map nor gtfs-osm-sync use PTv2, which would support that

### LTS Tiled Map Service Layer
### Light Rail Platforms
`railway=platform`  
included in Bus?

### Light Rail Stops
`railway=halt`  
already mapped

### Light Rail Track
`railway=light_rail`  
already mapped, and included in Bus?

### VTA ParkandRide
### VTA Transit Centers

## [San Jose official data download](http://www.sanjoseca.gov/index.aspx?NID=3308)
### Annexations
probably not useful
### Basemap
basemap.py  
see script for comments
* Parcels  
  used below
* Single Street Centerlines  
  `highway=*`  
  includes speedlimit and width, but otherwise already mapped  
  also bring up the "New Street"(?) thing
* Divided Street Centerlines  
  same

### Basemap 2
basemap2.py; basemap.js uses Parcels to correlate Address Points with Building Footprints  
not sure what to do with condos
* Address Points  
  `addr:*=*`
* Building Footprints  
  `building=yes`  
  very out of date. includes height and elevation. would need to conflate with existing building traces, turn some into building:parts, and check each if up-to-date.
* Condo Points  
  doesn't have anything relating it to anything specific
* Intersections  
  script translates certain kinds into `highway=motorway_junction` and "non-intersections," but neither are really useful (mostly already mapped)
* Side Walk Areas  
  `highway=footway`  
  already imported, and is made of polygons, not lines
* Tract Boundaries  
  only used by government. It could be used to outline landuse areas, but there are no such tags.

### City Council Districts
### City Limits
I thought not useful, but apparently there was a wish for this?

### General Plan
### Sanitary Systems
sanitary.py  
there is a spec for manholes, and even pipes, but not sure how useful it all is
* SanitaryPumpStation  
  `pumping_station=sewage`
* SanitaryGravityMain  
  `man_made=pipeline`
* SanitaryManhole  
  `man_made=manhole`
* SanitaryPressurizedMain  
  `man_made=pipeline`

### Storm Systems
stormwater.py  
marginally more useful than above, since detentions (basins) and culverts are above ground  
would need merging effort
* Stormwater_swGravityMain, Stormwater_swPressurizedMain, Stormwater_swLateralLine  
  `man_made=pipeline`
* Stormwater_swManhole  
  `man_made=manhole`
* Stormwater_swInlet  
  `man_made=storm_drain`
* Stormwater_swPumpStation  
  `pumping_station=wastewater`
* Stormwater_swOpenDrain  
  `waterway=drain`
* Stormwater_swDetention  
  `landuse=basin`
* Stormwater_swCulvert  
  `tunnel=culvert`

### Survey Benchmark Locations
benchmark.py  
`man_made=survey_point`  
not sure how useful

### Zoning
zoning.py, expand.js  
`landuse=*`  
works around streets (needs lots of cleanup)

## [County of Santa Clara open data portal](https://data.sccgov.org/browse?sortBy=alpha)
Datasets available as GeoJSON

### Points of Interest
scc poi.py  
`amenity=*`  
fire/police stations, schools… has some address info, but some outdated, and all already mapped

### Population by 2010 Census Tract
probably not useful

### Certified Healthy Nail Salons
nails.py  
`shop=beauty`  
weird, but actually mostly unmapped! poor geolocating though

### AddressPoint
### AirportsOutline
### CadastralMapgrids500
### CadastralMapgridsXY
### City Limits
### County Boundary (Area)
### Downtown SJC
### General Plan
### HospitalsAreas
### LandPolygon
### Parcels
### Railroads
### RoadsMajor
### SchoolsAreas
### Streetedge
### Unincorporated Areas
### Zoning
`landuse=*`  
seems to be sparse

## [San Jose maps gallery](http://gis.sanjoseca.gov/apps/mapsgallery/)

### DOT/DOT_MapsGallery_StreetTrees_M
trees.py

## [San Jose ArcGIS server](https://geo.sanjoseca.gov/server/rest/services)
Part or whole can be downloaded with download mapserer.py. Need to index and survey in full.

### DOT/DOT_TreeKeeper_StreetTrees_M
trees.py

## [Santa Clara County ArcGIS server](https://www.sccgov.org/gis/rest/services)
Part or whole can be downloaded with download mapserer.py. Need to index and survey in full.

