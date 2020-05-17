def filterLayer(layer):
    if layer.GetName() == "lines2":
        return layer

def filterTags(attrs):
    tags = {"highway": "footway",
            "footway": "sidewalk",
            "surface": "paved"}
    if int(attrs["adacomply"]):
        tags["wheelchair"] = "yes"
    if attrs["meterwidth"]:
        tags["width"] = "%.1f"%float(attrs["meterwidth"])
    return tags

