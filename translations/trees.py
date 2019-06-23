import math

def filterTags(attrs):
    tags = {"natural": "tree",
            "species": attrs["NAMESCIENTIFIC"]}
    if attrs["DIAMETER"]:
        tags["diameter_crown"] = str(int(round(float(attrs["DIAMETER"])*0.3048)))
    if attrs["HEIGHT"]:
        tags["height"] = str(int(round(float(attrs["HEIGHT"])*0.3048)))
    if attrs["TRUNKDIAM"]:
        diamInches = float(attrs["TRUNKDIAM"])
        circInches = math.pi*diamInches
        circMeters = circInches*0.0254
        tags["circumference"] = str(round(circMeters, 1))
    return tags

