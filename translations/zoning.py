# -*- coding: utf8 -*-

def filterLayer(layer):
    if layer is None:
        print("filterLayer: empty")
        return None
    print(layer.GetName())
    #layer.SetSpatialFilterRect(6161510, 1914285, 6167021, 1919180)
    return layer

def filterTags(attrs):
    if attrs is None:
        print("filterTags: empty")
        return None
    
    tags = {}#{"sjc:zoning": attrs["ZONING"], "sjc:pduse": attrs["PDUSE"]}
    
    if attrs["ZONING"] in ("Commercial Offi", "Industrial Park", "Commercial Gene"):
        tags["landuse"] = "commercial"
    elif attrs["ZONING"] in ("Heavy Industria", "Light Industria", "Main Street Com"):
        tags["landuse"] = "industrial"
    elif attrs["ZONING"] in ("Mobilehome Park", "Multiple Reside", "Rural Residenti", "Cluster (R-1-8", "Single-Family R", "Two-Family Resi", "Cluster (R-1-5"):
        tags["landuse"] = "residential"
    elif attrs["ZONING"] == ("Main Street Gro", "Commercial Neig", "Commercial Pede", "Downtown Primar"):
        tags["landuse"] = "retail"
    elif attrs["ZONING"] == "Agriculture":
        tags["landuse"] = "farmland"
    elif attrs["ZONING"] == "Water":
        tags["natural"] = "water"
    elif attrs["ZONING"] == "Planned Develop":
        if attrs["PDUSE"] == "Cemetary":
            tags["landuse"] = "cemetary"
        elif attrs["PDUSE"] in ("Res", "Multi-Family Re"):
            tags["landuse"] = "residential"
        elif attrs["PDUSE"] in ("CP", "Ind"):
            tags["landuse"] = "commercial"
        elif attrs["PDUSE"] in ("Com", "Com/Restaurant"):
            tags["landuse"] = "retail"
        #elif attrs["PDUSE"] == :
        #    tags["landuse"] = "industrial"
        elif attrs["PDUSE"] == "Hotel/Motel":
            tags["tourism"] = "hotel"
        else:
            # nothing more specific, but keep around to prevent others taking space
            tags["area"] = "yes"
    else:
        tags["area"] = "yes"
    
    return tags

