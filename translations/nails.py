import re

def filterTags(attrs):
    city = attrs["city"]
    if city.isupper():
        city = city.title()
    name = attrs["name"]
    if name.isupper():
        name = name.title()
    
    tags = {"shop": "beauty",
            "beauty": "nails",
            "name": name,
            "addr:city": city,
            "addr:postcode": attrs["zip"],
            "contact:phone": re.sub(r"\(?([0-9]{3})\)?[ -]([0-9 +-]{8,})", r"+1 \1 \2", attrs["phone_number"])}
    
    i = attrs["address"].find(" ")
    tags["addr:housenumber"] = attrs["address"][:i]
    street = attrs["address"][i+1:]
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
    
    return tags

