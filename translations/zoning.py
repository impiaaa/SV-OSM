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
    
    tags = {"sjc:zoning": attrs["ZONING"], "sjc:pduse": attrs["PDUSE"]}
    
    if attrs["ZONING"] in ("Commercial Pede", "Commercial Gene", "Main Street Com", "Commercial Offi", "Main Street Gro", "Downtown Primar"):
        tags["landuse"] = "commercial"
    elif attrs["ZONING"] in ("Heavy Industria", "Industrial Park", "Light Industria"):
        tags["landuse"] = "industrial"
    elif attrs["ZONING"] in ("Mobilehome Park", "Multiple Reside", "Rural Residenti", "Cluster (R-1-8", "Single-Family R", "Two-Family Resi", "Cluster (R-1-5"):
        tags["landuse"] = "residential"
    elif attrs["ZONING"] == "Commercial Neig":
        tags["landuse"] = "retail"
    elif attrs["ZONING"] == "Agriculture":
        tags["landuse"] = "farmland"
    elif attrs["ZONING"] == "Water":
        tags["natural"] = "water"
    elif attrs["ZONING"] == "Planned Develop":
        if attrs["PDUSE"] == "Cemetary":
            tags["landuse"] = "cemetary"
        elif attrs["PDUSE"] == "Res":
            tags["landuse"] = "residential"
        elif attrs["PDUSE"] in ("Com", "CP"):
            tags["landuse"] = "commercial"
        elif attrs["PDUSE"] == "Multi-Family Re":
            tags["landuse"] = "residential"
        elif attrs["PDUSE"] == "Com/Restaurant":
            tags["landuse"] = "retail"
        elif attrs["PDUSE"] == "Ind":
            tags["landuse"] = "industrial"
        elif attrs["PDUSE"] == "Hotel/Motel":
            tags["tourism"] = "hotel"
        else:
            # nothing more specific, but keep around to prevent others taking space
            tags["area"] = "yes"
    else:
        tags["area"] = "yes"
    
    return tags

