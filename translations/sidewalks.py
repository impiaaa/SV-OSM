def filterLayer(layer):
    if layer.GetName() == "linestrings2":
        return layer

def filterTags(attrs):
    return {"highway": "footway",
            "footway": "sidewalk",
            "wheelchair": ["no", "yes"][int(attrs["adacomply"])]}

