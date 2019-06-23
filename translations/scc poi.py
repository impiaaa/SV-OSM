import datetime

def filterTags(attrs):
    name = attrs["placename"]
    if name.isupper():
        name = name.title()
    
    tags = {"name": name,
            "addr:city": attrs["location_1_city"],
            "addr:postcode": attrs["location_1_zip"],
            "source": attrs["source"]}
    
    i = attrs["location_1_address"].find(" ")
    housenumber = attrs["location_1_address"][:i]
    if i != -1 and housenumber.isdigit():
        tags["addr:housenumber"] = housenumber
        street = attrs["location_1_address"][i+1:]
        i = street.rfind(" ")
        if street[i+1:].isdigit():
            tags["addr:unit"] = street[i+1:]
            street = street[:i]
        elif street[1].isspace() and street[0].isalpha() and street[0] not in "NSEW":
            tags["addr:unit"] = street[0]
            street = street[2:]
        elif street[-2].isspace() and street[-1].isalpha() and street[-1] not in "NSEW":
            tags["addr:unit"] = street[-1]
            street = street[:-2]
        
        if street.isupper():
            street = street.title()
        
        tags["addr:street"] = street
    else:
        tags["addr:full"] = attrs["location_1_address"]
    
    if attrs["lastupdate"]:
        tags["scc:LastUpdate"] = datetime.datetime.strptime(attrs["lastupdate"], "%Y/%m/%d %H:%M:%S")
    
    if attrs["placetype"] == "City Hall":
        tags["amenity"] = "townhall"
        tags["townhall:type"] = "city"
    elif attrs["placetype"] == "Clinic":
        tags["amenity"] = "clinic"
    elif attrs["placetype"] == "Community Center":
        tags["amenity"] = "community_centre"
    elif attrs["placetype"] == "Court":
        tags["amenity"] = "courthouse"
    elif attrs["placetype"] == "FireStation":
        tags["amenity"] = "fire_station"
    elif attrs["placetype"] == "Hospital":
        tags["amenity"] = "hospital"
    elif attrs["placetype"] == "Library":
        tags["amenity"] = "library"
    elif attrs["placetype"] == "Open Space":
        pass
    elif attrs["placetype"] == "Park":
        tags["leisure"] = "park"
    elif attrs["placetype"] == "Police":
        tags["amenity"] = "police"
    elif attrs["placetype"] == "Railroad Station":
        tags["railway"] = "station"
    elif attrs["placetype"] == "School":
        tags["amenity"] = "school"
    elif attrs["placetype"] == "Stadium":
        tags["leisure"] = "stadium"
    elif attrs["placetype"] == "Town Hall":
        tags["amenity"] = "townhall"
        tags["townhall:type"] = "town"
    elif attrs["placetype"] == "VTA Light Rail Station":
        tags["railway"] = "station"
        tags["station"] = "light_rail"
    
    return tags

def filterFeaturePost(feature, ogrfeature, ogrgeometry):
    if feature is None or feature.tags is None:
        return
    if "scc:LastUpdate" in feature.tags:
        feature.timestamp = feature.tags["scc:LastUpdate"]
        del feature.tags["scc:LastUpdate"]

