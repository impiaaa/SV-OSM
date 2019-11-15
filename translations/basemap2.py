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
    
    if layer.GetName() == "StreetIntersection":
        global IntTypeIndex
        defn = layer.GetLayerDefn()
        IntTypeIndex = defn.GetFieldIndex("INTTYPE")
    
    if layer.GetName() in ["StreetIntersection"]
        return layer
        
    # CondoPoint doesn't have anything relating it to anything specific.
    # TractBoundary is only used by government. It could be used to outline landuse areas, but there are no such tags.
    # SidewalkArea was already imported, and is made of polygons, not ways.

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature is None:
        print("filterFeature: empty")
        return
    
    if "INTTYPE" in fieldNames:
        global IntTypeIndex
        if ogrfeature.GetFieldAsString(IntTypeIndex) not in ("Ramp", "Non-Intersection"):
            return
    
    return ogrfeature

def filterTags(attrs):
    if attrs is None:
        print("filterTags: empty")
        return None
    
    if "ADACOMPLY" in attrs:
        # SidewalkArea
        tags = {"highway": "footway",
                "area": "yes",
                # Always appear, no equivalent
                "sjc:FacilityID": attrs["FACILITYID"]}
        # Always appear, has equivalent
        if attrs["ADACOMPLY"] == "Yes":
            tags["wheelchair"] = "yes"
            
        # Unused: WIDTH, AREA
        
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

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    if "sjc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["sjc:LastUpdate"]
        del feature.tags["sjc:LastUpdate"]

