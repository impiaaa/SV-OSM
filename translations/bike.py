def filterTags(attrs):
    tags = {}
    if attrs["SURFACE"] == "Gravel":
        tags["surface"] = "gravel"
    elif attrs["SURFACE"] == "Unpaved":
        tags["surface"] = "unpaved"
    elif attrs["SURFACE"] == "Paved":
        tags["surface"] = "paved"
    
    if attrs["TRAIL_NAME"]:
        tags["name"] = attrs["TRAIL_NAME"]
    
    if attrs["CLASS_TYPE"] == "Path":
        tags["highway"] = "path"
    elif attrs["CLASS_TYPE"] == "Cycle Track":
        tags["highway"] = "cycleway"
    elif attrs["SURFACE"] == "Service Road":
        tags["highway"] = "service"
        tags["bicycle"] = "yes"
    
    if attrs["CLASS_TYPE"] == "Lane":
        tags["cycleway"] = "lane"
    elif attrs["CLASS_TYPE"] == "Bike Route (Shared Roadway)":
        tags["cycleway"] = "shared_lane"
    elif attrs["CLASS_TYPE"] == "Bike Boulevard":
        tags["bicycle"] = "designated"
    
    return tags

