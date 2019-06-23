def filterTags(attrs):
    tags = {"man_made": "surveillance",
            "operator": "VTA",
            "surveillance:type": "camera",
            "surveillance:zone": "traffic"}
    if attrs["DIR"]:
        tags["direction"] = attrs["DIR"][0]
    tags["start_date"] = attrs["INSTALLED"][:10]
    if attrs["COMMENTS"]:
        tags["note"] = attrs["COMMENTS"]
    return tags

