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
    
    if layer.GetName() in ["Parcel"]: # "SingleStreets" # "DIVIDED_STREETS" duplicates SingleStreets
        return layer

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        print("filterFeature: empty")
        return
    if "MODELFLAG" in fieldNames and ogrfeature.GetFieldAsString(ogrfeature.GetFieldIndex("MODELFLAG")) == "M":
        # "merged" one-ways
        return
    return ogrfeature

def filterTags(attrs):
    if attrs is None:
        print("filterTags: empty")
        return None
    
    if "PARCELID" in attrs:
        # Parcel
        tags = {# Always appear, no equivalent
                "sjc:ParcelID": attrs["PARCELID"],
                "sjc:INTID": attrs["INTID"],
                "sjc:ParcelType": attrs["PARCELTYPE"],
                "sjc:LastUpdate": datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y/%m/%d")}
        
        # Sometimes appear, has equivalent
        if attrs["NOTES"]: tags["note"] = attrs["NOTES"]
        #if attrs["COVERED"] == "No": tags["covered"] = "no"
        if attrs["COVERED"]: tags["sjc:Covered"] = attrs["COVERED"]
        
        # Sometimes appear, no equivalent
        if attrs["APN"]: tags["sjc:APN"] = attrs["APN"]
        if attrs["LOTNUM"]: tags["sjc:LotNum"] = attrs["LOTNUM"]
        if attrs["LUDESC"]: tags["sjc:LUDesc"] = attrs["LUDESC"]
        if attrs["PLANCRT"]: tags["sjc:PlanCRT"] = attrs["PLANCRT"]
        if attrs["PLANMOD"]: tags["sjc:PlanMOD"] = attrs["PLANMOD"]
        
        # Unused: LUSUBDESC, FEATURECLA
        
        return tags
    
    if "FACILITYID" in attrs:
        # SingleStreets/DIVIDED_STREETS
        tags = {# Always appear, has equivalent
                "maxspeed": attrs["SPEEDLIMIT"]+" mph",
                # Always appear, no equivalent
                "sjc:FacilityID": attrs["FACILITYID"],
                "sjc:INTID": attrs["INTID"],
                "sjc:ToInterID": attrs["TOINTERID"],
                "sjc:LastUpdate": datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y/%m/%d")}
        if attrs["FULLNAME"] != "New Street": tags["name"] = attrs["FULLNAME"]
        
        # Sometimes appear, has equivalent
        if attrs["MODELFLAG"] == "D": tags["oneway"] = {"Both": "no", "To-From": "-1", "From-To": "yes"}[attrs["ONEWAYDIR"]]
        if attrs["PRIVATE"] == "Yes": tags["access"] = "private"
        if attrs["OFFICIAL"] == "Yes" or attrs["PRIVATE"] == "Yes":
            tags["highway"] = {"Freeway": "primary", "Residential": "residential", "Neighborhood Collect": "tertiary", "Highway": "motorway", "Major Arterial": "secondary"}[attrs["FUNCTCLASS"]]
        else:
            tags["highway"] = {"Freeway": "primary_link", "Residential": "unclassified", "Neighborhood Collect": "tertiary_link", "Highway": "motorway_link", "Major Arterial": "secondary_link"}[attrs["FUNCTCLASS"]]
        if attrs["FOCWIDTH"]: tags["width"] = str(float(attrs["FOCWIDTH"]))+" ft"
        if attrs["NOTES"]: tags["note"] = attrs["NOTES"]

        # Sometimes appear, no equivalent
        if attrs["FROMLEFT"]: tags["sjc:FromLeft"] = attrs["FROMLEFT"]
        if attrs["TOLEFT"]: tags["sjc:ToLeft"] = attrs["TOLEFT"]
        if attrs["FROMRIGHT"]: tags["sjc:FromRight"] = attrs["FROMRIGHT"]
        if attrs["TORIGHT"]: tags["sjc:ToRight"] = attrs["TORIGHT"]
        if attrs["PLANCRT"]: tags["sjc:PlanCRT"] = attrs["PLANCRT"]
        if attrs["PLANMOD"]: tags["sjc:PlanMOD"] = attrs["PLANMOD"]
        if attrs["ROWWIDTH"]: tags["sjc:RowWidth"] = attrs["ROWWIDTH"]
        
        # SingleStreets only
        if "LASTEDITOR" in attrs: tags["sjc:LastEditor"] = attrs["LASTEDITOR"]
        
        # MUNILEFT, MUNIRIGHT, ZIPLEFT, ZIPRIGHT
        # Unused: STREETMAST, FROMINTERI, ADDRNUMTYP, STREETCLAS, FEATURECLA, GLOBALID, SHAPE_LENG
        
        return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    
    if "sjc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["sjc:LastUpdate"]
        del feature.tags["sjc:LastUpdate"]
    
    if "oneway" in feature.tags and feature.tags["oneway"] == "-1":
        feature.geometry.points.reverse()
        feature.tags["oneway"] = "yes"

