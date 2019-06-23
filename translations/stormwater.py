import datetime

materials = {
"ABS Plastic": "plastic",
"Asbestos Cement": "asbestos_cement",
"Brick": "brick",
"Cast Iron": "cast_iron",
"Concrete (Non-Reinforced)": "concrete",
"Concrete Pipe (non-reinforced)": "concrete",
"Corrugated Metal Pipe": "corrugated_metal",
"Ductile Iron": "ductile_iron",
"Ductile Iron Pipe": "ductile_iron_pipe",
"High Density Polyethylene": "plastic",
"Polyethylene": "plastic",
"Polyvinyl Chloride": "plastic",
"Reinforced Concrete": "reinforced_concrete",
"Reinforced Concrete with T-Lock": "reinforced_concrete",
"Reinforced Plastic (Truss)": "reinforced_concrete",
"Spirolite": "plastic",
"Steel Pipe": "steel",
"Vitrified Clay": "clay"
}

def filterTags(attrs):
    tags = {}
    tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y%m%d%H%M%S")
    if attrs["NOTES"]:
        tags["note"] = attrs["NOTES"]
    
    if "FITTINGTYP" in attrs:
        # Stormwater_swFitting
        pass
    elif "PUMPTYPE" in attrs:
        # Stormwater_swPumpStation
        tags["pumping_station"] = "wastewater"
        tags["substance"] = "drain"
        if attrs["PUMPTYPE"] not in ("", "Unknown"):
            tags["pumping_station:type"] = attrs["PUMPTYPE"].lower().replace(" ", "_")
        if attrs["ELEVATION"]:
            tags["ele"] = str(round(float(attrs["ELEVATION"])*0.30480060960121924, 1))
        if attrs["INLETDIAM"]:
            tags["diameter"] = str(round(float(attrs["INLETDIAM"].strip('"'))*2.5400051, 0))
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
        if attrs["ACTIVEFLAG"] == "True":
            tags["man_made"] = "pumping_station"
        else:
            tags["disused:man_made"] = "pumping_station"
    elif "STRUCTTYPE" in attrs:
        # Stormwater_swNetworkStructure
        pass
    elif "MHTYPE" in attrs:
        # Stormwater_swManhole
        tags["man_made"] = "manhole"
        tags["manhole"] = "rainwater"
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
    elif "DEVICETYPE" in attrs:
        # Stormwater_swCleanOut
        pass
    elif "DISCHARGET" in attrs:
        # Stormwater_swDischargePoint
        pass
    elif "INLETTYPE" in attrs:
        # Stormwater_swInlet
        tags["man_made"] = "storm_drain"
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
    elif "ODTYPE" in attrs:
        # Stormwater_swOpenDrain
        tags["waterway"] = "drain"
        if attrs["WIDTH"]:
            tags["width"] = str(round(float(attrs["WIDTH"].strip('"'))*0.025400051, 0))
    elif "DETTYPE" in attrs:
        # Stormwater_swDetention
        tags["landuse"] = "basin"
        if attrs["NAME"]:
            tags["name"] = attrs["NAME"]
        if attrs["DETTYPE"] == "Percolation":
            tags["basin"] = "infiltration"
        elif attrs["DETTYPE"] == "Detention":
            tags["basin"] = "detention"
        elif attrs["DETTYPE"] in ("Bioretention", "Retention"):
            tags["basin"] = "retention"
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
    elif "CULVERTSHA" in attrs:
        # Stormwater_swCulvert
        tags["tunnel"] = "culvert"
        if attrs["MATERIAL"] in materials:
            tags["material"] = materials[attrs["MATERIAL"]]
        if attrs["DIAMETER"] not in ("", "Other"):
            tags["width"] = str(round(float(attrs["DIAMETER"].strip('"'))*0.025400051, 0))
    else:
        # Stormwater_swGravityMain, Stormwater_swPressurizedMain, Stormwater_swLateralLine
        tags["man_made"] = "pipeline"
        tags["location"] = "underground"
        #tags["pressure"] = "yes"
        tags["substance"] = "drain"
        if attrs["DIAMETER"] and attrs["DIAMETER"].strip('"').split(".")[0].isdigit():
            tags["diameter"] = str(round(float(attrs["DIAMETER"].strip('"'))*2.5400051, 0))
        if attrs["MATERIAL"] in materials:
            tags["material"] = materials[attrs["MATERIAL"]]
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
    
    return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    if "sjc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["sjc:LastUpdate"]
        del feature.tags["sjc:LastUpdate"]

