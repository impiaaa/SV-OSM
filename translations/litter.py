def filterLayer(layer):
    if layer.GetName() == "Public Litter Cans":
        return layer

def filterTags(attrs):
    tags = {"amenity": "waste_basket"}
    col = []
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        if attrs[day.upper()] and int(attrs[day.upper()]):
            col.append(day[:2])
    if len(col) > 0:
        tags["collection_times"] = ";".join(col)
    return tags

