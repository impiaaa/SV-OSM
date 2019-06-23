import datetime

def filterTags(attrs):
    if attrs is None:
        print("filterTags: empty")
        return None
    
    tags = {"man_made": "survey_point",
            "ref": attrs["REFERENCEM"],
            "description": attrs["LOCDESCRIP"]}
    
    if attrs["ELEVATIONF"]:
        tags["ele"] = str(round(float(attrs["ELEVATIONF"])*0.304800609601219241, 1))
    if attrs["LASTUPDATE"]:
        tags["sjc:LastUpdate"] = datetime.datetime.strptime(attrs["LASTUPDATE"], "%Y%m%d%H%M%S")
    
    return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    if "sjc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["sjc:LastUpdate"]
        del feature.tags["sjc:LastUpdate"]

