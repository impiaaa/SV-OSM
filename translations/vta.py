from osgeo import ogr
from geom import *
import urllib, math, datetime

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

# idea: figure out once and for all which ID's are unique. find duplicates by POINTS LIST and list common/different keys

# active VTA transit editors: andygol, seattlefyi, njtbusfan, richlv, Edward, wheelmap_android, Dvorty, Minh Nguyen, stevea, whjms, dhogan, mark7, bibi6, Dr Kludge, Alexander Avtanski, huonw, Ropino, clay_c, ErikPottinger, KindredCoda, StellanL, n76, jgkamat, gaku, 217541OSM

def filterLayer(layer):
    if layer is None:
        print "filterLayer: empty"
        return None
    print layer.GetName()
    if layer.GetName() == "Bus_2018" and False:
        idFieldId1 = layer.GetLayerDefn().GetFieldIndex("DESTINATIONSI")
        idFieldId2 = layer.GetLayerDefn().GetFieldIndex("PATTERN_JAN2019_SP_LINEDIRID")
        routePoints = {}
        routeIndices = {}
        i = 0
        while i < layer.GetFeatureCount():
            ogrfeature = layer.GetFeature(i)
            if ogrfeature is None:
                i += 1
                continue
            geo = ogrfeature.GetGeometryRef()
            if geo is None:
                i += 1
                continue
            if geo.GetGeometryCount() > 1:
                # for now
                layer.DeleteFeature(i)
                print "filterLayer: deleted feature", i, "split too much"
                continue
            points = geo.GetGeometryRef(0).GetPoints()
            if points is None:
                i += 1
                continue
            lineId = ogrfeature.GetFieldAsString(idFieldId1)+ogrfeature.GetFieldAsString(idFieldId2)
            if lineId in routeIndices:
                if points in routePoints[lineId]:
                    layer.DeleteFeature(i)
                    print "filterLayer: deleted feature", i, lineId, "true duplicate"
                    continue
                else:
                    routeIndices[lineId].append(i)
                    routePoints[lineId].append(points)
            else:
                routeIndices[lineId] = [i]
                routePoints[lineId] = [points]
            i += 1
        layer.ResetReading()
        distFieldId = layer.GetLayerDefn().GetFieldIndex("DISTANCE")
        for lineId, indices in routeIndices.items():
            if len(indices) > 0:
                # delete all but the longest route of the same name
                # not sure this is a good idea - some routes skip stops on some days but are numbered the same
                indices.sort(key=lambda i: layer.GetFeature(i).GetFieldAsDouble(distFieldId), reverse=True)
                for i in indices[1:]:
                    layer.DeleteFeature(i)
                    print "filterLayer: deleted feature", i, lineId, "short duplicate"
        
    return layer

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        print "filterFeature: empty"
        return
    geo = ogrfeature.GetGeometryRef()
    #if geo is None:
    #    print "filterFeature: empty geometry", ogrfeature.GetFID()
    #    return
    #if geo.GetGeometryType() == ogr.wkbPoint:
    #    pt = geo.GetPoint()
    #else:
    #    pt = geo.Centroid().GetPoint()
    #if pt[0] < -121.9167566 or \
    #    pt[1] < 37.3412814 or \
    #    pt[0] > -121.873985 or \
    #    pt[1] > 37.3662764:
    #    print "filterFeature: out of bounds"
    #    return
    #if pt[0] < -121.8749174 or \
    #    pt[1] < 37.2442858 or \
    #    pt[0] > -121.8560212 or \
    #    pt[1] > 37.2575915:
    #    print "filterFeature: out of bounds"
    #    return
    if "feature" in fieldNames:
        # Stops, from Bus_Stop_Inventory
        return ogrfeature
    elif "LINE_TYPE" in fieldNames:
        # Lines, from Bus_2018
        return ogrfeature
    else:
        print "filterFeature: unknown schema", fieldNames
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
routeNameFixes = routeNameFixes.items()
routeNameFixes.sort(key=lambda a: len(a[0]), reverse=True)

def filterTags(attrs):
    if not attrs:
        print "filterTags: empty"
        return
    tags = {}
    if "feature" in attrs:
        # Stops, from Bus_Stop_Inventory
        
        # Public transport schema V1
        
        if attrs["rtiid"]:
            tags["ref"] = attrs["rtiid"]
            tags["gtfs_id"] = str(int(attrs["rtiid"])-60000)
        if attrs["stopname"]:
            tags["name"] = attrs["stopname"]
            if tags["name"].isupper() or tags["name"].islower():
                tags["name"] = tags["name"].title()
        tags["operator"] = "Santa Clara Valley Transportation Authority"
        #tags["operator"] = "Santa Clara Valley Transit Authority" # ???
        if attrs["feature"] == "Bus Stop":
            tags["bus"] = "yes"
        elif attrs["feature"] == "LR Stop":
            tags["light_rail"] = "yes"
        if attrs["ada_accessible"]:
            if attrs["ada_accessible"] == "No":
                tags["wheelchair"] = "no"
            elif attrs["ada_accessible"] == "Yes":
                tags["wheelchair"] = "yes"
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
        #tags["tactile_paving"]
        #tags["toilet"]


        # Seen on existing stops, no schema
        
        #if attrs["tactile_signs"] and attrs["tactile_signs"].lower() != "none":
        #    tags["information"] = "tactile_letters"
        if attrs["feature"] == "Bus Stop":
            tags["highway"] = "bus_stop"
        elif attrs["feature"] == "LR Stop":
            tags["railway"] = "platform"
        
        
        # Public transit schema V2
        
        tags["public_transport"] = "platform"
        #tags["local_ref"]
        tags["network"] = "VTA"
        if attrs["others_using_stop"] not in ["", "nnone", ",none", "none", "no", "no ", "No", "bike lane", "bike route", "transit signs", "Turn Off Engine Sign", "yes"]:
            others = attrs["others_using_stop"].strip().replace("  ", ";").replace(",", ";").replace("; ", ";")
            if (others.isupper() and len(others) > 6) or others.islower():
                others = others.title()
            tags["network"] += ";"+others
        #tags["covered"]
        if "schedule" in attrs["other_info_sign"] or "schedual" in attrs["other_info_sign"]:
            tags["departures_board"] = "yes"
        #tags["layer"]
        if attrs["lighting_nearby"]:
            #if attrs["lighting_nearby"] == "Shelter Light":
            #    tags["lit"] = "yes"
            #elif attrs["lighting_nearby"].startswith("Solar Light"):
            #    tags["lit"] = "yes"
            if attrs["lighting_nearby"] == "None":
                tags["lit"] = "no"
            else:
                # Does S.L. other side count?
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


        routes_listed = attrs["routes_listed"]
        if attrs["route_number"] not in ["", "Null", "none", "Other"] and attrs["route_number"] not in attrs["routes_listed"]:
            routes_listed += ";"+attrs["route_number"]
        for find, replace in routeNameFixes:
            routes_listed = routes_listed.replace(find, replace)
        routes_listed = routes_listed.strip()
        if routes_listed:
            # used to associate with route ways, removed in preOutputTransform
            #tags["routes"] = set(routes_listed.split())
            tags["route_ref"] = routes_listed.replace(" ", ";").strip(";")
        
        if not any([r.isdecimal() or r.upper() == "55X" for r in routes_listed.split()]):
            del tags["operator"]
        
        if attrs["date_updated"]: tags["vta:date_updated"] = attrs["date_updated"]
        if attrs["date_visited"]: tags["vta:date_visited"] = attrs["date_visited"]
        tags["vta:last_modified"] = attrs["last_modified"]
        if attrs["comments"]: tags["note"] = attrs["comments"]
        # VTA tags without a translation
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
                print repr(attrs["DESTINATIONSI"]), repr(attrs["LINEABBR"])
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
            #tags["name"] = attrs["DESTINATIONSI"].title().strip() # XXX
            #print "parsing", attrs["DESTINATIONSI"]
            to = attrs["DESTINATIONSI"][attrs["DESTINATIONSI"].find(' ', len(attrs["LINEABBR"]))+1:]
            if " via " in to.lower():
                i = to.lower().find(" via ")
                tags["via"] = to[i+5:].strip().title()
                #print "parsed via", tags["via"]
                to = to[:i]
            tags["to"] = to.strip().title()
            #print "parsed to", tags["to"]
            if False:#to[:12] in attrs["LINENAME"]:
                # LINENAME is either FROM - TO or TO - FROM.
                # DESTINATIONSI is always the destination (to).
                # Figure out if DESTINATIONSI is closer to the start or the end of LINENAME,
                # and use the other half for "from."
                j1 = attrs["LINENAME"].find(to[:12])
                #j2 = min(j1 + len(to), len(attrs["LINENAME"]))
                j2 = j1+min(12, len(to))
                while j2 < len(attrs["LINENAME"]) and j2-j1 < len(to) and attrs["LINENAME"][j2] == to[j2-j1]: j2 += 1
                if j1 > len(attrs["LINENAME"])-j2:
                    while (attrs["LINENAME"][j1-1].isspace() or attrs["LINENAME"][j1-1] == "-") and j1 > 0:
                        j1 -= 1
                    tags["from"] = attrs["LINENAME"][:j1].title()
                else:
                    while (attrs["LINENAME"][j2].isspace() or attrs["LINENAME"][j2] == "-") and j2 < len(attrs["LINENAME"]):
                        j2 += 1
                    tags["from"] = attrs["LINENAME"][j2:].title()
                #print "parsed from", tags["from"]
        else:
            #tags["name"] = attrs["LINEABBR"]+" "+attrs["DESTINATIONSI"].title().strip() # XXX
            tags["official_name"] = attrs["LINENAME"].title().strip()
        #if attrs["LINE_TYPE"] != "Light Rail":
        #    if frm == to:
        #        tags["name"] = "Bus {ref}".format(ref=tags["ref"])
        #    elif via:
        #        tags["name"] = "Bus {ref}: {frm} => {via} => {to}".format(ref=tags["ref"], frm=frm, to=to, via=via)
        #    else:
        #        tags["name"] = "Bus {ref}: {frm} => {to}".format(ref=tags["ref"], frm=frm, to=to)
        
        #if tags["ref"] and "from" in tags and "to" in tags and "via" in tags:
        #    tags["name"] = "VTA {ref} {from} - {via} - {to}".format(**tags)
        #elif tags["ref"] and "from" in tags and "to" in tags and tags["from"] != tags["to"]:
        #    tags["name"] = "VTA {ref} {from} - {to}".format(**tags)
        if "ref" in tags and tags["ref"]:
            tags["name"] = "VTA {}".format(tags["ref"])
            if attrs["PATTERN"]:
                tags["name"] += " "+attrs["PATTERN"]
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
        print "filterTags: unknown schema", attrs
    return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None:
        return
    # vta:date_updated, vta:date_visited, vta:last_modified
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
        ts = datetime.datetime.strptime(feature.tags.pop("vta:date_visited")[:20], "%Y-%m-%dT%H:%M:%S.")
        if feature.timestamp is None or ts > feature.timestamp:
            feature.timestamp = ts
    if "vta:last_modified" in feature.tags:
        ts = datetime.datetime.strptime(feature.tags.pop("vta:last_modified")[:20], "%Y-%m-%dT%H:%M:%S.")
        if feature.timestamp is None or ts > feature.timestamp:
            feature.timestamp = ts

def getWayIndexForStop(stop, ways):
    # look for ways that have "stop" as the next stop
    for i, way in enumerate(ways):
        for f2 in way.parents:
            # lazy fuzzy match
            if "vta:dest" in f2.tags and f2.tags["vta:dest"][3:10] in stop.tags["name"]:
                return i

def pointAboveLine(pt, slope, intercept):
    if slope == float("inf"):
        return pt.x >= intercept
    else:
        return pt.y >= slope*pt.x + intercept

def preOutputTransform(geometries, features):
    if geometries is None and features is None:
        print "preOutputTransform: empty"
        return
    if False:
        uniqueRoutes = []
        routeFeatures = []
        routeWays = []
        routeWaysPoints = []
        i = 0
        while i < len(features):
            feat = features[i]
            if "route" in feat.tags:
                if "vta:objectid" in feat.tags:
                    ref = feat.tags.pop("vta:objectid")
                else:
                    ref = ""
                if "vta:dest" in feat.tags:
                    dest = feat.tags.pop("vta:dest")
                else:
                    dest = ""
                # filter unique routes (on linedirid), since there are multiple ways for each
                if feat.tags not in uniqueRoutes:
                    uniqueRoutes.append(feat.tags)
                    routeWays.append([feat.geometry])
                    routeWaysPoints.append([[(pt.x, pt.y) for pt in feat.geometry.points]])
                    #routeFeatures.append(feat)
                    #i += 1
                else:
                    # delete truly duplicate ways
                    j = uniqueRoutes.index(feat.tags)
                    pts = [(pt.x, pt.y) for pt in feat.geometry.points]
                    if pts not in routeWaysPoints[j]:
                        routeWays[j].append(feat.geometry)
                        routeWaysPoints[j].append(pts)
                    else:
                        del features[i]
                        geometries.remove(feat.geometry)
                        try:
                            feat.geometry.removeparent(feat)
                        except ValueError:
                            pass
                        feat.geometry = None
                        print "preOutputTransform: deleted", feat.tags
                        continue
                feat.tags = {}
                if ref:
                    feat.tags["ref"] = ref
                if dest:
                    feat.tags["vta:dest"] = dest
            i += 1
        
        # transform route ways into relations
        for route, ways in zip(uniqueRoutes, routeWays):
            feat = Feature()
            feat.tags = route
            relation = Relation()
            feat.geometry = relation
            relation.addparent(feat)
            
            relation.members.extend([(way, "") for way in ways])

            # look for associated stops
            if "ref" in route and route["ref"]:
                routeNo = route["ref"]
                #routeDir = route["vta:directionname"][0]
                stops = [feat for feat in features \
                        if "routes" in feat.tags and \
                        routeNo in feat.tags["routes"]]# and \
                        #getWayIndexForStop(feat, ways) >= 0]
                #stops.sort(key=lambda stop: stop.tags["vta:stop"])
                #relation.members.extend([(stop.geometry, "platform") for stop in stops])
                for stop in reversed(stops):
                    stop.geometry.addparent(relation)
                    idx = getWayIndexForStop(stop, ways)
                    m = (stop.geometry, "platform")
                    if idx is not None:
                        relation.members.insert(idx, m)
                    else:
                        relation.members.append(m)
            
            geometries.append(relation)
            features.append(feat)
    
    elif False:
        # transform route ways into relations
        for wayFeat in features:
            if isinstance(wayFeat.geometry, Way):
                if "route" not in wayFeat.tags:
                    print "preOutputTransform: way with no 'route' tag:", wayFeat.tags
                    continue
                relFeat = Feature()
                relFeat.tags = wayFeat.tags
                wayFeat.tags = {}
                relation = Relation()
                relFeat.geometry = relation
                relation.addparent(relFeat)
                relation.members.append((wayFeat.geometry, ""))
                geometries.append(relation)
                features.append(relFeat)
                
                if "ref" in relFeat.tags and relFeat.tags["ref"] and False:
                    routeNo = relFeat.tags["ref"]
                    # get stops on this route
                    stops = [feat for feat in features \
                             if "routes" in feat.tags and \
                             routeNo in feat.tags["routes"]]
                    if len(stops) == 0:
                        print "preOutputTransform: no stops on route", routeNo
                        continue
                    if len(wayFeat.geometry.points) <= 1:
                        print "preOutputTransform: empty way on route", routeNo
                        continue
                    # follow the route, look for stops on the way
                    for i in range(len(wayFeat.geometry.points)-1):
                        pt1 = wayFeat.geometry.points[i]
                        pt2 = wayFeat.geometry.points[i+1]
                        # y = m*x + b
                        # line of the segment
                        if pt1.x == pt2.x:
                            slope = float("inf")
                            intercept = pt1.x # use x-offset instead
                        else:
                            slope = float(pt2.y - pt1.y)/float(pt2.x - pt1.x)
                            intercept = pt1.y - int(slope*pt1.x)
                        #print "preOutputTransform", routeNo, pt1.x, pt1.y, pt2.x, pt2.y, slope, intercept
                        # lines perpendicular to the segment, intersecting the endpoints
                        # negative reciperocal slope
                        if pt1.y == pt2.y:
                            perpendicular = float("inf")
                            perpInter1 = pt1.x
                            perpInter2 = pt2.x
                        else:
                            perpendicular = -1.0*float(pt2.x - pt1.x)/float(pt2.y - pt1.y)
                            perpInter1 = pt1.y - perpendicular*pt1.x
                            perpInter2 = pt2.y - perpendicular*pt2.x
                        # line parallel to the segment but offset to the right
                        d = 0.0003*1e9 # needs tweaking
                        if pt2.y < pt1.y: d *= -1
                        # to travel d units along the perpendicular line, move by this much on each axis
                        if pt1.y == pt2.y:
                            ptOffX = 0.0
                            ptOffY = d
                        else:
                            ptOffX = d / math.sqrt(perpendicular**2 + 1)
                            ptOffY = d*perpendicular / math.sqrt(perpendicular**2 + 1)
                        # intercept of the line parallel
                        if pt1.x == pt2.x:
                            interOff = intercept + ptOffX
                        else:
                            interOff = (ptOffY+intercept) - slope*ptOffX
                        
                        for stop in stops:
                            # if a stop is in an inside curve, don't add it twice
                            if isinstance(relation.members[-1][0], Point) and \
                               relation.members[-1][0].x == stop.geometry.x and \
                               relation.members[-1][0].y == stop.geometry.y:
                                continue
                            # look inside the box (way segment line<->right offset, bottom<->top)
                            # the XOR part is to check for directionality
                            # (i.e., check for stops north of the segment if heading west, south if heading east)
                            if ((pt2.x >= pt1.x) ^ pointAboveLine(stop.geometry, slope, intercept)) and \
                               ((pt2.x < pt1.x) ^ pointAboveLine(stop.geometry, slope, interOff)) and \
                               ((pt2.y <= pt1.y) ^ pointAboveLine(stop.geometry, perpendicular, perpInter1)) and \
                               ((pt2.y > pt1.y) ^ pointAboveLine(stop.geometry, perpendicular, perpInter2)):
                                stop.geometry.addparent(relation)
                                relation.members.append((stop.geometry, "platform"))
                    print "preOutputTransform: route", routeNo, "has", len(stops), "stops,", len(relation.members)-1, "are on", relFeat.tags["name"]
                #else:
                #    print "preOutputTransform: no ref on", relFeat.tags["name"]
    
    # delete "routes" internal tag
    for feat in features:
        if "routes" in feat.tags:
            del feat.tags["routes"]

