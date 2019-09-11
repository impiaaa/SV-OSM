from osgeo import ogr
from geom import *
import urllib.request, urllib.parse, urllib.error, math, datetime

# sed s/OGRGeoJSON/Bus_Stop_Inventory/g Bus_Stop_Inventory.kml > Bus_Stop_Inventory-rename.kml
# sed "s/OGRGeoJSON/Bus_2018/g;s/F_JANUARY_2019___//g" Bus_2018.kml > Bus_2018-rename.kml
# cat Bus*-rename.kml > Bus_combined.kml
# nano Bus_combined.kml
# sed -E "s/([0-9.-]+,[0-9.-]+)<.coordinates><.LineString><LineString><coordinates>\1/\1/g" Bus_combined.kml > Bus_joined.kml
# sed -E "s/([0-9.-]+,[0-9.-]+)<.coordinates><.LineString><LineString><coordinates>([0-9.-]+,[0-9.-]+) \1<.coordinates><.LineString><LineString><coordinates>\2/\1 \2/g" Bus_joined.kml > Bus_fix1.kml
# sed -E "s/<MultiGeometry><LineString><coordinates>([0-9.-]+,[0-9.-]+) ([0-9.-]+,[0-9.-]+)<.coordinates><.LineString><LineString><coordinates>\1/<MultiGeometry><LineString><coordinates>\2 \1/g" Bus_fix1.kml > Bus_fix2.kml
# sed -E "s/([0-9.-]+,[0-9.-]+)<.coordinates><.LineString><LineString><coordinates>([0-9.-]+,[0-9.-]+) \1<.coordinates><.LineString><.MultiGeometry>/\1 \2<\/coordinates><\/LineString><\/MultiGeometry>/g" Bus_fix2.kml > Bus_fix3.kml
# grep -v "</coordinates></LineString><LineString><coordinates>" Bus_fix3.kml > Bus_fix4.kml # optional
# python ogr2osm.py Bus_fix4.kml -t translations/vta.py -v -f

# sed 's/F_JANUARY_2019___//g;s/"LINEABBR":null,//g;s/"LINENAME":null,//g;s/"LINE_TYPE":null,//g;s/"DIRECTIONNAME":null,//g;s/"PATTERN":null,//g;s/"DISTANCE":null,//g;s/"PATTERNID":null,//g;s/"SIGNUPNAME":null,//g' Bus_2018.geojson > Bus_2018-rename.geojson
# sed -E "s/([0-9.-]+,[0-9.-]+)\]\],\[\[\1/\1/g" Bus_2018-rename.geojson > Bus_2018-fix1.geojson
# sed -E "s/(\[[0-9.-]+,[0-9.-]+\])\],\[(\[[0-9.-]+,[0-9.-]+\]),\1\],\[\2/\1,\2/g" Bus_2018-fix1.geojson > Bus_2018-fix2.geojson
# sed -E "s/(\[[0-9.-]+,[0-9.-]+\]),(\[[0-9.-]+,[0-9.-]+\])\],\[\1,\2/\1,\2/g" Bus_2018-fix2.geojson > Bus_2018-fix3.geojson

# idea: figure out once and for all which ID's are unique. find duplicates by POINTS LIST and list common/different keys

# active VTA transit editors: andygol, seattlefyi, njtbusfan, richlv, Edward, wheelmap_android, Dvorty, Minh Nguyen, stevea, whjms, dhogan, mark7, bibi6, Dr Kludge, Alexander Avtanski, huonw, Ropino, clay_c, ErikPottinger, KindredCoda, StellanL, n76, jgkamat, gaku, 217541OSM

def filterLayer(layer):
    if layer is None:
        print("filterLayer: empty")
        return None
    if layer.GetName() == "Bus_Stop_Inventory":
        # Stops, from Bus_Stop_Inventory
        global StatusFieldIndex
        StatusFieldIndex = layer.GetLayerDefn().GetFieldIndex("trapeze_status")
    print(layer.GetName())
    
    return layer

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        print("filterFeature: empty")
        return
    geo = ogrfeature.GetGeometryRef()
    if "feature" in fieldNames:
        # Stops, from Bus_Stop_Inventory
        if ogrfeature.GetFieldAsString(StatusFieldIndex) not in ("Active", ""):
            # skip: Inactive, Proposed, Temporary, Under Construction, Under Review
            return
        return ogrfeature
    elif "LINE_TYPE" in fieldNames:
        # Lines, from Bus_2018
        return ogrfeature
    else:
        print("filterFeature: unknown schema", fieldNames)
        return

routeNameFixes = {
"(77)": "", # other stop transfer, I think
"NB": "", # could maybe be used for figuring out the route
"SB": "",
"EB": "",
"WB": "",
"Inactive": "",
"INACTIVE STOP": "",
"DASH": "201",
"(const. closure - 2015)": "",
"EMPTY BAY": "",
"EMPTY BAY (COMMUNITY SHUTTLE)": "",
"none": "",

# Regional services
"HWY-17": "970",
"DB": "971",
"DB-EXP": "971",
"MST-55": "972",
"MST 55": "972",

# Not in system
"MTN VIEW SHUTTLE": "824",
"MARGUERITE": "",
"22MARGUERITE": "22",
"ACE": "",#"822 823 824 825 826 827 828 831", # these routes are listed, but we can't tell which one
"ACE (fremont bart)": "",
"ACE (none)": "",
"CALTRAIN": "",
"CALTRIAN": "",
"SAMTRANS": "",
"Amtrak": "",
"AMTRK": "",
"MST-86": "",
"GREYHOUND": "",
"SAN BENITO CO TRANS": "",
"SAN JOAQUIN TRANSIT": "",

# drop-off only (TODO: use platform_exit_only)
"DROP OFF": "",
"drop-off": "",
"DROP-OFF": "",
"Drop-off Layover": "",
"Drop off only": "",
"DROP ONLY (49ER)": "",
"DROP STOP": "",
"77 layover only": "",
"Levi stadium drop off": "",
"LAYOVER": "",
"Layover": "",
"LAYOVER (BAY 2)": "",
"LAYOVER (BAY 3)": "",
"LAYOVER (BAY 4)": "",
"layover only": "",

# pick-up only (TODO)
"pick-up stop": "",
}
routeNameFixes = list(routeNameFixes.items())
routeNameFixes.sort(key=lambda a: len(a[0]), reverse=True)

def filterTags(attrs):
    if not attrs:
        print("filterTags: empty")
        return
    tags = {}
    if "feature" in attrs:
        # Stops, from Bus_Stop_Inventory
        
        # Public transport schema V1
        
        if attrs["rtiid"]:
            tags["ref"] = attrs["rtiid"]
            #tags["gtfs_id"] = str(int(attrs["rtiid"])-60000)
        if attrs["stopname"]:
            # Most (but not all) VTA stop names are not properly title-case
            if attrs["stopname"].isupper() or attrs["stopname"].islower():
                tags["name"] = attrs["stopname"].title()
            else:
                tags["name"] = attrs["stopname"]
        tags["operator"] = "Santa Clara Valley Transportation Authority"
        # Some stops have "Santa Clara Valley Transit Authority" instead
        if attrs["feature"] == "Bus Stop":
            tags["bus"] = "yes"
        elif attrs["feature"] == "LR Stop":
            tags["light_rail"] = "yes"
        if attrs["ada_accessible"]:
            if attrs["ada_accessible"] == "No":
                tags["wheelchair"] = "no"
            elif attrs["ada_accessible"] == "Yes":
                tags["wheelchair"] = "yes"
        # Count how many of each type of bench there are
        benches_known = False
        benches = 0
        for key in "ad_bench", "metal_vta_benches", "private_benches", "vta_bench":
            if attrs[key]:
                benches_known = True
                benches += int(attrs[key])
        if benches_known:
            if benches > 0:
                tags["bench"] = "yes"
            else:
                tags["bench"] = "no"
        if attrs["vta_trash_container"]:
            if int(attrs["vta_trash_container"]) > 0:
                tags["bin"] = "yes"
            else:
                tags["bin"] = "no"
        if attrs["shelter"]:
            if attrs["shelter"] == "NO":
                tags["shelter"] = "no"
            else:
                tags["shelter"] = "yes"
        # No matching VTA tag
        #tags["tactile_paving"]
        #tags["toilet"]


        # Seen on existing stops, no schema or not related to PT schema
        
        if attrs["tactile_signs"] and attrs["tactile_signs"].lower() != "none":
            tags["information"] = "tactile_letters"
        if attrs["feature"] == "Bus Stop":
            tags["highway"] = "bus_stop"
        elif attrs["feature"] == "LR Stop":
            tags["railway"] = "platform"
        if attrs["comments"]:
            tags["note"] = attrs["comments"]
        
        
        # Public transit schema V2
        
        tags["public_transport"] = "platform"
        tags["network"] = "VTA"
        # Attempt to clean up "others_using_stop" field and use it to list other joint bus networks
        if attrs["others_using_stop"] not in ["", "nnone", ",none", "none", "no", "no ", "No", "bike lane", "bike route", "transit signs", "Turn Off Engine Sign", "yes"]:
            others = attrs["others_using_stop"].strip().replace("  ", ";").replace(",", ";").replace("; ", ";")
            if (others.isupper() and len(others) > 6) or others.islower():
                others = others.title()
            tags["network"] += ";"+others
        if "schedule" in attrs["other_info_sign"] or "schedual" in attrs["other_info_sign"]:
            tags["departures_board"] = "yes"
        if attrs["lighting_nearby"]:
            if attrs["lighting_nearby"] == "None":
                tags["lit"] = "no"
            else:
                # Does "S.L. other side" count?
                tags["lit"] = "yes"
        if attrs["boarding_pavement"]:
            if attrs["boarding_pavement"] == "AC - Asphalt Paving":
                tags["surface"] = "asphalt"
            elif attrs["boarding_pavement"] == "Brick":
                tags["surface"] = "paving_stones"
            elif attrs["boarding_pavement"] == "Dirt":
                tags["surface"] = "dirt"
            elif attrs["boarding_pavement"] == "Gravel":
                tags["surface"] = "gravel"
            elif attrs["boarding_pavement"] == "Landscape B.O. Curb":
                tags["surface"] = "grass"
            elif attrs["boarding_pavement"] == "Pavers":
                tags["surface"] = "paving_stones"
            elif attrs["boarding_pavement"] == "PCC Concrete":
                tags["surface"] = "concrete"
        # No matching VTA tag
        #tags["local_ref"]
        #tags["covered"]
        #tags["layer"]

        # Attempt to clean up "route_number" and "routes_listed" VTA tags to use as "route_ref" OSM tag
        routes_listed = attrs["routes_listed"]
        if attrs["route_number"] not in ["", "Null", "none", "Other"] and attrs["route_number"] not in attrs["routes_listed"]:
            routes_listed += ";"+attrs["route_number"]
        for find, replace in routeNameFixes:
            routes_listed = routes_listed.replace(find, replace)
        routes_listed = routes_listed.strip()
        if routes_listed:
            tags["route_ref"] = routes_listed.replace(" ", ";").strip(";")
        
        # Except for 55X, all VTA lines are decimal, so if there are any non-numbers in the route list, it's not actually served by VTA.
        if not any([r.isdecimal() or r.upper() == "55X" for r in routes_listed.split()]):
            del tags["operator"]
        
        # Parsed and put into the actual node timestamp in filterFeaturePost
        if attrs["date_updated"]:
            tags["vta:date_updated"] = attrs["date_updated"]
        if attrs["date_visited"]:
            tags["vta:date_visited"] = attrs["date_visited"]
        tags["vta:last_modified"] = attrs["last_modified"]
        
        # VTA tags without a directly matching OSM tag
        if False:
            tags["vta:amigo_id"] = attrs["amigo_id"]
            if attrs["ac_asphalt_paving"]: tags["vta:ac_asphalt_paving"] = attrs["ac_asphalt_paving"]
            if attrs["accessible_path_to_crossing"]: tags["vta:accessible_path_to_crossing"] = attrs["accessible_path_to_crossing"]
            if attrs["ad_bench"]: tags["vta:ad_bench"] = attrs["ad_bench"]
            #if attrs["ada_accessible"]: tags["vta:ada_accessible"] = attrs["ada_accessible"]
            if attrs["adjacent_property"]: tags["vta:adjacent_property"] = attrs["adjacent_property"]
            if attrs["adopt_a_stop"]: tags["vta:adopt_a_stop"] = attrs["adopt_a_stop"]
            if attrs["atname"]: tags["vta:atname"] = attrs["atname"]
            if attrs["bench_pad"]: tags["vta:bench_pad"] = attrs["bench_pad"]
            if attrs["boarding_area"]: tags["vta:boarding_area"] = attrs["boarding_area"]
            #if attrs["boarding_pavement"]: tags["vta:boarding_pavement"] = attrs["boarding_pavement"]
            if attrs["city"]: tags["vta:city"] = attrs["city"]
            if attrs["comments"]: tags["vta:comments"] = attrs["comments"]
            if attrs["commercial_property"]: tags["vta:commercial_property"] = attrs["commercial_property"]
            if attrs["concrete_sidewalk"]: tags["vta:concrete_sidewalk"] = attrs["concrete_sidewalk"]
            if attrs["curb_cuts"]: tags["vta:curb_cuts"] = attrs["curb_cuts"]
            if attrs["date_updated"]: tags["vta:date_updated"] = attrs["date_updated"]
            if attrs["date_visited"]: tags["vta:date_visited"] = attrs["date_visited"]
            #if attrs["feature"]: tags["vta:feature"] = attrs["feature"]
            if attrs["government_property"]: tags["vta:government_property"] = attrs["government_property"]
            if attrs["information_sign"]: tags["vta:information_sign"] = attrs["information_sign"]
            if attrs["jurisdiction"]: tags["vta:jurisdiction"] = attrs["jurisdiction"]
            tags["vta:last_modified"] = attrs["last_modified"]
            #if attrs["lat"]: tags["vta:lat"] = attrs["lat"]
            if attrs["lighting_nearby"]: tags["vta:lighting_nearby"] = attrs["lighting_nearby"]
            #if attrs["long"]: tags["vta:long"] = attrs["long"]
            if attrs["metal_vta_benches"]: tags["vta:metal_vta_benches"] = attrs["metal_vta_benches"]
            if attrs["no_improvements"]: tags["vta:no_improvements"] = attrs["no_improvements"]
            if attrs["onname"]: tags["vta:onname"] = attrs["onname"]
            if attrs["other_agencies_signs"]: tags["vta:other_agencies_signs"] = attrs["other_agencies_signs"]
            if attrs["other_info_sign"]: tags["vta:other_info_sign"] = attrs["other_info_sign"]
            if attrs["other_pad_type"]: tags["vta:other_pad_type"] = attrs["other_pad_type"]
            if attrs["other_pole"]: tags["vta:other_pole"] = attrs["other_pole"]
            if attrs["other_property"]: tags["vta:other_property"] = attrs["other_property"]
            if attrs["others_using_stop"]: tags["vta:others_using_stop"] = attrs["others_using_stop"]
            if attrs["parking_restrictions"]: tags["vta:parking_restrictions"] = attrs["parking_restrictions"]
            if attrs["pavement_condition"]: tags["vta:pavement_condition"] = attrs["pavement_condition"]
            if attrs["pcc_bus_pad"]: tags["vta:pcc_bus_pad"] = attrs["pcc_bus_pad"]
            if attrs["pcc_bus_pad_length"]: tags["vta:pcc_bus_pad_length"] = attrs["pcc_bus_pad_length"]
            if attrs["pole"]: tags["vta:pole"] = attrs["pole"]
            if attrs["private_benches"]: tags["vta:private_benches"] = attrs["private_benches"]
            if attrs["residential"]: tags["vta:residential"] = attrs["residential"]
            if attrs["route_number"]: tags["vta:route_number"] = attrs["route_number"]
            if attrs["routes_listed"]: tags["vta:routes_listed"] = attrs["routes_listed"]
            if attrs["rs_sat_alight"]: tags["vta:rs_sat_alight"] = attrs["rs_sat_alight"]
            if attrs["rs_sat_board"]: tags["vta:rs_sat_board"] = attrs["rs_sat_board"]
            if attrs["rs_sun_alight"]: tags["vta:rs_sun_alight"] = attrs["rs_sun_alight"]
            if attrs["rs_sun_board"]: tags["vta:rs_sun_board"] = attrs["rs_sun_board"]
            if attrs["rs_wkdy_alight"]: tags["vta:rs_wkdy_alight"] = attrs["rs_wkdy_alight"]
            if attrs["rs_wkdy_board"]: tags["vta:rs_wkdy_board"] = attrs["rs_wkdy_board"]
            if attrs["rti"]: tags["vta:rti"] = attrs["rti"]
            if attrs["rti_decal"]: tags["vta:rti_decal"] = attrs["rti_decal"]
            #if attrs["rtiid"]: tags["vta:rtiid"] = attrs["rtiid"]
            if attrs["school"]: tags["vta:school"] = attrs["school"]
            #if attrs["shelter"]: tags["vta:shelter"] = attrs["shelter"]
            if attrs["shelter_pad"]: tags["vta:shelter_pad"] = attrs["shelter_pad"]
            if attrs["sidewalk_width"]: tags["vta:sidewalk_width"] = attrs["sidewalk_width"]
            if attrs["simmie_seat"]: tags["vta:simmie_seat"] = attrs["simmie_seat"]
            #if attrs["sp_documents"]: tags["vta:sp_documents"] = attrs["sp_documents"]
            if attrs["sp_g"]: tags["vta:sp_g"] = attrs["sp_g"]
            if attrs["sp_gat"]: tags["vta:sp_gat"] = attrs["sp_gat"]
            if attrs["sp_gwt"]: tags["vta:sp_gwt"] = attrs["sp_gwt"]
            if attrs["st_dir"]: tags["vta:st_dir"] = attrs["st_dir"]
            if attrs["st_loc"]: tags["vta:st_loc"] = attrs["st_loc"]
            if attrs["standard_vta_sign"]: tags["vta:standard_vta_sign"] = attrs["standard_vta_sign"]
            if attrs["stop"]: tags["vta:stop"] = attrs["stop"]
            if attrs["stopabbr"]: tags["vta:stopabbr"] = attrs["stopabbr"]
            #if attrs["stopname"]: tags["vta:stopname"] = attrs["stopname"]
            if attrs["street_view"]: tags["vta:street_view"] = attrs["street_view"]
            if attrs["tactile_signs"]: tags["vta:tactile_signs"] = attrs["tactile_signs"]
            if attrs["tc_other"]: tags["vta:tc_other"] = attrs["tc_other"]
            if attrs["tc_with_shelter"]: tags["vta:tc_with_shelter"] = attrs["tc_with_shelter"]
            if attrs["trapeze_id"]: tags["vta:trapeze_id"] = attrs["trapeze_id"]
            if attrs["trapeze_status"]: tags["vta:trapeze_status"] = attrs["trapeze_status"]
            if attrs["two_sided_sign"]: tags["vta:two_sided_sign"] = attrs["two_sided_sign"]
            if attrs["vta_trash_container"]: tags["vta:vta_trash_container"] = attrs["vta_trash_container"]
            if attrs["vta_bench"]: tags["vta:vta_bench"] = attrs["vta_bench"]
            tags["vta:ESRI_OID"] = attrs["ESRI_OID"]
            tags["vta:index"] = attrs["index"]
    elif "LINE_TYPE" in attrs:
        # Lines, from Bus_2018
        # Imported as ways, but the information will be transfered to a relation
        
        
        # Public transit schema V2
        
        tags["type"] = "route"
        if attrs["LINE_TYPE"] == "Light Rail":
            tags["route"] = "light_rail"
        else:
            # different kinds of bus lines--should we distinguish?
            tags["route"] = "bus"

        if attrs["DESTINATIONSI"].startswith(attrs["LINEABBR"]) and attrs["DESTINATIONSI"] and attrs["LINEABBR"]:
            i = attrs["DESTINATIONSI"].find(" ", len(attrs["LINEABBR"]))
            if i == -1:
                print(repr(attrs["DESTINATIONSI"]), repr(attrs["LINEABBR"]))
                tags["ref"] = attrs["LINEABBR"]
            else:
                tags["ref"] = attrs["DESTINATIONSI"][:i]
        else:
            tags["ref"] = attrs["LINEABBR"]
        
        tags["public_transport:version"] = "2"
        #tags["roundtrip"]
        if attrs["LINE_TYPE"]:
            tags["operator"] = "Santa Clara Valley Transportation Authority" # ???
            #tags["operator"] = "Santa Clara Valley Transit Authority" # ???
        else:
            tags["ref:VTA"] = tags["ref"]
            del tags["ref"]
        tags["network"] = "VTA"
        #tags["opening_hours"]
        #tags["interval"]
        #tags["duration"]
        #tags["fee"]
        #tags["bicycle"]
        #tags["wheelchair"]
        # DESTINATIONSI(gn) is what the vehicle sign says; can be the next stop (lr), line name (shuttle), or ultimate destination (bus)
        if attrs["DESTINATIONSI"].startswith(attrs["LINEABBR"]) and attrs["DESTINATIONSI"] and attrs["LINEABBR"]:
            to = attrs["DESTINATIONSI"][attrs["DESTINATIONSI"].find(' ', len(attrs["LINEABBR"]))+1:]
            if to.lower().startswith(attrs["LINE_TYPE"].lower()):
                to = to[len(attrs["LINE_TYPE"])+1:]
            if " via " in to.lower():
                i = to.lower().find(" via ")
                tags["via"] = to[i+5:].strip().title()
                to = to[:i]
            tags["to"] = to.strip().title()
        #tags["official_name"]
        #tags["colour"] # 900=E3670F, 901=008FD5, 902=7FBF4F
        
        
        # Other common tags
        
        if attrs["DIRECTIONNAME"]:
            # N/S/E/W
            tags["direction"] = attrs["DIRECTIONNAME"][0]
        if attrs["SCHEDULES"] != "http://www.vta.org/routes/rt":
            tags["website"] = attrs["SCHEDULES"]
        if attrs["LINEABBR"]: tags["gtfs_route_id"] = attrs["LINEABBR"]
        #tags["gtfs_shape_id"] = attrs["LINEABBR"]+"_"+attrs["PATTERN"]
        #tags["gtfs_trip_headsign"] = attrs["DESTINATIONSI"]
        if attrs["LINEABBR"]: tags["gtfs_route_short_name"] = attrs["LINEABBR"]
        tags["gtfs_route_long_name"] = attrs["LINENAME"]

        # VTA tags without a translation
        if True:
            if attrs["PATTERN_JAN2019_SP_LINEDIRID"]: tags["vta:linedirid"] = attrs["PATTERN_JAN2019_SP_LINEDIRID"] # unique on direction+lineabbr
            #if attrs["LINEABBR"]: tags["vta:lineabbr"] = attrs["LINEABBR"]
            #if attrs["LINENAME"]: tags["vta:linename"] = attrs["LINENAME"]
            if attrs["LINE_TYPE"]: tags["vta:line_type"] = attrs["LINE_TYPE"]
            if attrs["DIRECTIONNAME"]: tags["vta:directionname"] = attrs["DIRECTIONNAME"]
            if attrs["PATTERN"]: tags["vta:pattern"] = attrs["PATTERN"]
            if attrs["DISTANCE"]: tags["vta:distance"] = attrs["DISTANCE"]
            if attrs["PATTERNID"]: tags["vta:patternid"] = attrs["PATTERNID"]
            if attrs["SIGNUPNAME"]: tags["vta:signupname"] = attrs["SIGNUPNAME"]
            if attrs["DESTINATIONSI"]: tags["vta:destinationsi"] = attrs["DESTINATIONSI"]
            #if attrs["SHAPELEN"]: tags["vta:shapelen"] = attrs["SHAPELEN"]
    else:
        print("filterTags: unknown schema", attrs)
    return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None:
        return
    if "vta:date_updated" in feature.tags:
        t = feature.tags.pop("vta:date_updated")
        while not t[-1].isdigit(): t = t[:-1]
        while not t[0].isdigit(): t = t[1:]
        if "/" in t:
            if ":" in t:
                feature.timestamp = datetime.datetime.strptime(t, "%m/%d/%Y %H:%M")
            elif t.rfind("/") < len(t)-3:
                feature.timestamp = datetime.datetime.strptime(t, "%m/%d/%Y")
            else:
                feature.timestamp = datetime.datetime.strptime(t, "%m/%d/%y")
        elif "-" in t and ":" in t:
            feature.timestamp = datetime.datetime.strptime(t[:20], "%Y-%m-%dT%H:%M:%S.")
        else:
            if t.find("-") > 2:
                feature.timestamp = datetime.datetime.strptime(t, "%Y-%m-%d")
            else:
                feature.timestamp = datetime.datetime.strptime(t, "%m-%d-%Y")
    if "vta:date_visited" in feature.tags:
        ts = datetime.datetime.strptime(feature.tags.pop("vta:last_modified")[:19], "%Y/%m/%d %H:%M:%S")
        if feature.timestamp is None or ts > feature.timestamp:
            feature.timestamp = ts
    if "vta:last_modified" in feature.tags:
        ts = datetime.datetime.strptime(feature.tags.pop("vta:last_modified")[:19], "%Y/%m/%d %H:%M:%S")
        if feature.timestamp is None or ts > feature.timestamp:
            feature.timestamp = ts

