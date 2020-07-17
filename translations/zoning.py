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
    
    tags = {}#{"sjc:zoning": attrs["zoningabbrev"], "sjc:pduse": attrs["pduse"]}
    
    zabbr = attrs["zoningabbrev"][:attrs["zoningabbrev"].find('(')] if '(' in attrs["zoningabbrev"] else attrs["zoningabbrev"]
    pduse = attrs["pduse"]
    
    if pduse == "Cemetary":
        tags["landuse"] = "cemetery"

    elif pduse == "Hotel/Motel":
        tags["tourism"] = "hotel"

    elif zabbr.startswith("R"):
        tags["landuse"] = "residential"
        if zabbr == "R-1-RR":
            tags["residential"] = "rural"
        elif zabbr == "R-MH":
            tags["residential"] = "halting_site"
        elif zabbr.startswith("R-1"):
            tags["residential"] = "single_family"
        elif zabbr.startswith("R-M"):
            tags["residential"] = "urban"
    
    elif pduse in ("Res", "Multi-Family Re"):
        tags["landuse"] = "residential"
    
    elif pduse in ("Com", "CIC"):
        tags["landuse"] = "commercial"
    
    elif pduse in ("CP", "Com/Restaurant", "Retail and Park"):
        tags["landuse"] = "retail"
    
    elif attrs["zoningabbrev"] == "A":
        tags["landuse"] = "farmland"
    
    elif zabbr in ("CO", "CIC", "IP"):
        tags["landuse"] = "commercial"
    
    elif zabbr in ("CP", "CN", "CG", "MS-C"):
        tags["landuse"] = "retail"
    
    elif zabbr in ("LI", "HI"):
        tags["landuse"] = "industrial"
    
    elif zabbr == "WATER":
        tags["natural"] = "water"
    
    return tags

