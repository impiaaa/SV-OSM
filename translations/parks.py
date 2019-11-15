from datetime import datetime

def filterFeature(ogrfeature, fieldNames, reproject):
    if ogrfeature.GetFieldAsString(ogrfeature.GetFieldIndex('PARKTYPE')) in ('OS', 'JU', 'TR', 'PRVOS', 'CFD'):
        return
    return ogrfeature

def filterTags(attrs):
    tags = {"name": attrs['NAME'],
            "operator": attrs['OWNER']}
    if attrs['PARKTYPE'] in ('NEIG', 'REG', 'DOT'):
        tags["leisure"] = "park"
    elif attrs['PARKTYPE'] == 'HISCU':
        tags["historic"] = "yes"
    elif attrs['PARKTYPE'] == 'GOLF':
        tags["leisure"] = "golf_course"
    elif attrs['PARKTYPE'] == 'COMGRD':
        if attrs['SUBCLASS'] == 'OS':
            tags["landuse"] = "allotments"
        elif attrs['SUBCLASS'] == 'COMGRD':
            tags["leisure"] = "garden"
    elif attrs['PARKTYPE'] == 'CIV':
        tags["amenity"] = "fire_station"
    elif attrs['PARKTYPE'] == 'DOG':
        tags["leisure"] = "dog_park"
    elif attrs['PARKTYPE'] == 'SPRT':
        tags["leisure"] = "sports_centre"
    elif attrs['PARKTYPE'] == 'CC':
        tags["amenity"] = "community_centre"
    
    if attrs['ADDRESS']:
        tags["addr:full"] = attrs['ADDRESS']
    if attrs['DATEOPENED']:
        tags["start_date"] = datetime.fromtimestamp(int(attrs['DATEOPENED'])/1000).isoformat()[:10]
    if attrs['NAMEALIAS'] and attrs['NAMEALIAS'] != attrs['NAME']:
        tags["alt_name"] = attrs['NAMEALIAS']
    return tags

