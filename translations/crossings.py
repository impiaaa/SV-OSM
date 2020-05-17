def filterLayer(layer):
    if layer.GetName() in {"intersection", "curbramps", "ramplines", "crossing"}:
        return layer

def filterFeature(ogrfeature, fieldNames, reproject):
    if "trafficcontroltype" not in fieldNames: return ogrfeature
    xct = ogrfeature.GetFieldAsString(ogrfeature.GetFieldIndex("trafficcontroltype"))
    if xct in ("Signal", "Yield Sign"): return ogrfeature
    ict = ogrfeature.GetFieldAsString(ogrfeature.GetFieldIndex("intersectiontype"))
    if xct.endswith(" Way Stop") and len(ict) > 0: return ogrfeature

def filterTags(attrs):
    if "trafficcontroltype" in attrs:
        # intersection
        if attrs["trafficcontroltype"] == "Signal":
            return {"highway": "traffic_signals"}
        elif attrs["trafficcontroltype"] == "Yield Sign":
            return {"highway": "give_way"}
        elif attrs["trafficcontroltype"].endswith(" Way Stop") and len(attrs["intersectiontype"]) > 0:
            legs = int(attrs["intersectiontype"][0])
            stops = int(attrs["trafficcontroltype"][0])
            if stops >= legs:
                return {"highway": "stop", "stop": "all"}
            else:
                return {"highway": "priority"}
    elif "ramptype" in attrs:
        # curbramps
        tags = {"barrier": "kerb"}
        if attrs["ramptype"].startswith("Parallel"):
            tags["kerb"] = "flush"
        elif attrs["ramptype"].startswith("Perpendicular"):
            tags["kerb"] = "lowered"
        if attrs["adaoverallcompliance"] == "Compliant":
            tags["wheelchair"] = "yes"
        return tags
    elif "incline" in attrs:
        # ramplines
        tags = {"highway": "footway",
                "footway": "sidewalk",
                "surface": "paved",
                "incline": attrs["incline"]}
        if int(attrs["adacomply"]):
            tags["wheelchair"] = "yes"
        return tags
    elif "withincrosswalk" in attrs:
        # crossing
        tags = {"highway": "footway",
                "footway": "crossing"}
        if attrs["withincrosswalk"]:
            marked = int(attrs["withincrosswalk"])
            tags["crossing"] = "marked" if marked else "unmarked"
        if attrs["adaoverallcompliance"] == "Compliant":
            tags["wheelchair"] = "yes"
        return tags

