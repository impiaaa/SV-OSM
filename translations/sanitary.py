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
    
    if "FITTINGTYP" in attrs:
        # SanitaryFitting
        pass
    elif "PUMPTYPE" in attrs:
        # SanitaryPumpStation
        tags["pumping_station"] = "sewage"
        tags["substance"] = "sewage"
        if attrs["PUMPTYPE"] not in ("", "Unknown"):
            tags["pumping_station:type"] = attrs["PUMPTYPE"].lower().replace(" ", "_")
        if attrs["ELEVATION"]:
            tags["ele"] = str(round(float(attrs["ELEVATION"])*0.30480060960121924, 1))
        if attrs["INLETDIAM"]:
            tags["diameter"] = str(round(float(attrs["INLETDIAM"][:-1])*2.5400051, 0))
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        if attrs["MAINTBY"] not in ("", "Private"):
            tags["operator"] = attrs["MAINTBY"]
        if attrs["ACTIVEFLAG"] == "True":
            tags["man_made"] = "pumping_station"
        else:
            tags["disused:man_made"] = "pumping_station"
        tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y%m%d%H%M%S")
        if attrs["NOTES"]:
            tags["note"] = attrs["NOTES"]
    elif "STRUCTTYPE" in attrs:
        # SanitaryNetworkStructure
        pass
    elif "FEATURECLA" in attrs:
        # SanitaryGravityMain
        tags["man_made"] = "pipeline"
        tags["location"] = "underground"
        tags["pressure"] = "no"
        tags["substance"] = "sewage"
        if attrs["DIAMETER"] and attrs["DIAMETER"][:-1].split(".")[0].isdigit():
            tags["diameter"] = str(round(float(attrs["DIAMETER"][:-1])*2.5400051, 0))
        if attrs["MATERIAL"] in materials:
            tags["material"] = materials[attrs["MATERIAL"]]
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
        tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y%m%d%H%M%S")
        if attrs["NOTES"]:
            tags["note"] = attrs["NOTES"]
    elif "MHTYPE" in attrs:
        # SanitaryManhole
        tags["man_made"] = "manhole"
        tags["manhole"] = "sewer"
        if attrs["INST_YEAR"]:
            tags["start_date"] = attrs["INST_YEAR"]
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
        tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y%m%d%H%M%S")
        if attrs["NOTES"]:
            tags["note"] = attrs["NOTES"]
    else:
        # SanitaryPressurizedMain
        tags["man_made"] = "pipeline"
        tags["location"] = "underground"
        tags["pressure"] = "yes"
        tags["substance"] = "sewage"
        tags["diameter"] = str(round(float(attrs["DIAMETER"][:-1])*2.5400051, 0))
        if attrs["MATERIAL"] in materials:
            tags["material"] = materials[attrs["MATERIAL"]]
        if attrs["OWNEDBY"] == "Private":
            tags["access"] = "private"
        elif attrs["OWNEDBY"]:
            tags["operator"] = attrs["OWNEDBY"]
        tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y%m%d%H%M%S")
        if attrs["NOTES"]:
            tags["note"] = attrs["NOTES"]
    
    return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    if "sjc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["sjc:LastUpdate"]
        del feature.tags["sjc:LastUpdate"]

