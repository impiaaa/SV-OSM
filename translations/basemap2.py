from pprint import pprint
from osgeo import ogr
from geom import *
import datetime

def filterLayer(layer):
    if layer is None:
        print("filterLayer: empty")
        return None
    
    print(layer.GetName())
    
    #layer.SetSpatialFilterRect(6161510, 1914285, 6167021, 1919180)
    
    if layer.GetName() == "Site_Address_Points":
        global StatusFieldIndex, UnitTypeIndex
        defn = layer.GetLayerDefn()
        StatusFieldIndex = defn.GetFieldIndex("Status")
        UnitTypeIndex = defn.GetFieldIndex("Unit_Type")
    elif layer.GetName() == "StreetIntersection":
        global IntTypeIndex
        defn = layer.GetLayerDefn()
        IntTypeIndex = defn.GetFieldIndex("INTTYPE")
    
    if layer.GetName() in ["CondoParcel", "BuildingFootprint", "Site_Address_Points"]: # "StreetIntersection"
        return layer
        
    # CondoPoint doesn't have anything relating it to anything specific.
    # TractBoundary is only used by government. It could be used to outline landuse areas, but there are no such tags.
    # SidewalkArea was already imported, and is made of polygons, not ways.

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        print("filterFeature: empty")
        return
    
    if "FullMailin" in fieldNames:
        global StatusFieldIndex, UnitTypeIndex
        if ogrfeature.GetFieldAsString(StatusFieldIndex) not in ("Active", "Existing"):
            # skip: Unverified, Temporary, Retired
            return
        if ogrfeature.GetFieldAsString(UnitTypeIndex) in ("Apartment", "Basement", "Upper"):
            # likely in the same building
            return
    elif "INTTYPE" in fieldNames:
        global IntTypeIndex
        if ogrfeature.GetFieldAsString(IntTypeIndex) not in ("Ramp", "Non-Intersection"):
            return
    
    return ogrfeature

SURVEY_FEET_TO_METER = 1200.0/3937.0

def filterTags(attrs):
    if attrs is None:
        print("filterTags: empty")
        return None

    if "PARCELID" in attrs:
        # CondoParcel
        # Always appear, no equivalent
        tags = {"sjc:INTID": attrs["INTID"]}
        val = attrs["LASTUPDATE"]
        if "/" in val:
            tags["sjc:LastUpdate"] = datetime.datetime.strptime(val, "%Y/%m/%d")
        else:
            tags["sjc:LastUpdate"] = datetime.datetime.strptime(val, "%Y%m%d%H%M%S")

        # Sometimes appear, has equivalent
        val = attrs["NOTES"]
        if val: tags["note"] = val
        
        # Sometimes appear, no equivalent
        val = attrs["PARCELID"]
        if val: tags["sjc:ParcelID"] = val
        val = attrs["PLANCRT"]
        if val: tags["sjc:PlanCRT"] = val
        val = attrs["PLANMOD"]
        if val: tags["sjc:PlanMOD"] = val
        
        # Unused: CONDOPARCE, LENGTH, AREA
        
        return tags
    
    if "ADACOMPLY" in attrs:
        # SidewalkArea
        tags = {"highway": "footway",
                "area": "yes",
                # Always appear, no equivalent
                "sjc:FacilityID": attrs["FACILITYID"]}
        # Always appear, has equivalent
        if attrs["ADACOMPLY"] == "Yes":
            tags["wheelchair"] = "yes"
        if attrs["COVERED"] == "Yes":
            tags["covered"] = "yes"
            
        # Unused: WIDTH, AREA
        
        return tags

    if "BLDGELEV" in attrs:
        # BuildingFootprint
        tags = {"building": "yes",
                # Always appear, has equivalent
                "height": "%.02f"%round(float(attrs["BLDGHEIGHT"])*SURVEY_FEET_TO_METER, 2),
                "ele": "%.02f"%round(float(attrs["BLDGELEV"])*SURVEY_FEET_TO_METER, 2),
                # Always appear, no equivalent
                "sjc:FacilityID": attrs["FACILITYID"]}
        
        # Sometimes appear, no equivalent
        val = attrs["LASTUPDATE"]
        if val: tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y/%m/%d")
        
        # Unused: LENGTH, SHAPE_AREA
        
        return tags
    
    if "FullMailin" in attrs:
        # Site_Address_Points
        tags = {# Always appear, has equivalent
                "addr:city": attrs["Inc_Muni"],
                # Always appear, no equivalent
                "sjc:Site_NGUID": attrs["Site_NGUID"],
                "sjc:ESN": attrs["ESN"],
                "sjc:Status": attrs["Status"],
                "sjc:Juris_Auth": attrs["Juris_Auth"],
                "sjc:LastUpdate": datetime.datetime.strptime(attrs["LastUpdate"], "%Y%m%d%H%M%S"),
                "sjc:LastEditor": attrs["LastEditor"]}

        # Sometimes appear, has equivalent
        val = attrs["Add_Number"]
        if val: tags["addr:housenumber"] = val
        val = attrs["CompName"]
        if val: tags["addr:street"] = val
        val = attrs["Unit"]
        if val: tags["addr:unit"] = val
        val = attrs["Post_Code"]
        if val: tags["addr:postcode"] = val

        pt = attrs["Place_Type"]
        # Unit_Type is Apartment, Basement, Building, Office, Room, Space, Suite, Trailer, Unit, Upper
        if attrs["Unit_Type"] in ("Building", "Space", "") or attrs["Unit"] == "":
            # other Place_Type are Common Area (multi-use), Miscellaneous
            tags["building"] = {"Business": "commercial",
                                "Educational": "school",
                                "Faith Based Organiz": "religious",
                                "Government": "government",
                                "Hospital": "hospital",
                                "Hotel": "hotel",
                                "Mobile Home": "static_caravan",
                                "Multi Family": "residential",
                                "Restaurant": "retail",
                                "Retail": "retail",
                                "Single Family": "house"}.get(pt, "yes")
        
        #if pt == "Business":
            #tags["office"] = "yes"
        if pt == "Educational":
            tags["amenity"] = "school"
        elif pt == "Faith Based Organiz":
            tags["amenity"] = "place_of_worship"
        elif pt == "Government":
            tags["office"] = "government"
        elif pt == "Group Quarters":
            # salvation army
            tags["amenity"] = "social_facility"
        elif pt == "Hospital":
            tags["amenity"] = "hospital"
        elif pt == "Hotel":
            tags["tourism"] = "hotel"
        #elif pt == "Miscellaneous":
            #print pt, attrs["FullMailin"]
        #elif pt == "Mobile Home":
            #tags["building"] = "static_caravan"
        #elif pt == "Multi Family":
            #tags["building:use"] = "residential"
        elif pt == "Recreational":
            tags["club"] = "sport"
        elif pt == "Restaurant":
            tags["amenity"] = "restaurant"
        elif pt == "Retail":
            tags["shop"] = "yes"
        #elif pt == "Single Family":
            #tags["building"] = "detached"

        val = attrs["Source"]
        if val: tags["source"] = val
        val = attrs["Notes"]
        if val and not attrs["FullAddres"].upper().startswith(
            val[:10]
            .replace("NORTH", "N")
            .replace("SOUTH", "S")
            .replace("EAST", "E")
            .replace("WEST", "W")):
            tags["note"] = val

        # Sometimes appear, no equivalent
        val = attrs["RCL_NGUID"]
        if val: tags["sjc:RCL_NGUID"] = val
        val = attrs["StreetMast"]
        if val: tags["sjc:StreetMast"] = val
        val = attrs["ParcelID"]
        if val: tags["sjc:ParcelID"] = val
        val = attrs["CondoParce"]
        if val: tags["sjc:CondoParce"] = val
        val = attrs["UnitID"]
        if val: tags["sjc:UnitID"] = val
        val = attrs["RSN"]
        if val: tags["sjc:RSN"] = val
        val = attrs["PSAP_ID"]
        if val: tags["sjc:PSAP_ID"] = val
        val = attrs["AddNum_Suf"]
        if val: tags["sjc:AddNum_Suf"] = val
        val = attrs["Unit_Type"]
        if val: tags["sjc:Unit_Type"] = val
        val = attrs["Building"]
        if val: tags["sjc:Building"] = val
        val = attrs["FullUnit"]
        if val: tags["sjc:FullUnit"] = val
        val = attrs["Addtl_Loc"]
        if val: tags["sjc:Addtl_Loc"] = val
        val = attrs["LSt_Name"]
        if val: tags["sjc:LSt_Name"] = val
        val = attrs["LSt_Type"]
        if val: tags["sjc:LSt_Type"] = val
        val = attrs["Uninc_Comm"]
        if val: tags["sjc:Uninc_Comm"] = val
        val = attrs["Effective"]
        if val: tags["sjc:Effective"] = val
        
        # Always the same: Client_ID, County, State, Country, Placement, Post_Comm
        # Not used here: FullMailin, Lat, Long, GlobalID, FullAddres
        # Street name parts, could be used in a relation: St_PreDirA, St_PreTyp, StreetName, St_PosTyp, St_PosTypC, St_PosTypU, St_PosDir, Feanme, FullName
        # Unused in data set: Site_NGU00, AddNum_Pre, St_PreMod, St_PreDir, St_PreSep, St_PosMod, Floor, Room, Seat, Post_Code4, APN, LStPostDir, AddCode, AddDataURI, Nbrhd_Comm, MSAGComm, LandmkName, Mile_Post, Elev, Expire
        
        return tags
    
    if "INTTYPE" in attrs:
        # StreetIntersection
        tags = {# Always appear, no equivalent
                "sjc:FacilityID": attrs["FACILITYID"]}
        if attrs["INTTYPE"] == "Ramp":
            tags["highway"] = "motorway_junction"
        else:
            tags["sjc:IntType"] = attrs["INTTYPE"]
        # Sometimes appear, has equivalent
        val = attrs["INTNAME"]
        if val: tags["name"] = val
        
        return tags
    
    if "LOTNUM" in attrs:
        # CondoPoint
        tags = {# Always appear, no equivalent
                "sjc:INTID": attrs["INTID"]}
        
        # Sometimes appear, has equivalent
        val = attrs["NOTES"]
        if val: tags["note"] = val
        
        # Sometimes appear, no equivalent
        val = attrs["APN"]
        if val: tags["sjc:APN"] = val
        val = attrs["LOTNUM"]
        if val: tags["sjc:LotNum"] = val
        val = attrs["PLANCRT"]
        if val: tags["sjc:PlanCRT"] = val
        val = attrs["PLANMOD"]
        if val: tags["sjc:PlanMOD"] = val
        val = attrs["LASTUPDATE"]
        if val: tags["sjc:LastUpdate"] = datetime.datetime.strptime(val, "%Y%m%d%H%M%S")
        
        # Not used here: GlobalID
        # Unused in data set: CONDOUNITI, CONDOPARCE, LUDESC, LUSUBDESC
        
        return tags
    
def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    if "sjc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["sjc:LastUpdate"]
        del feature.tags["sjc:LastUpdate"]

