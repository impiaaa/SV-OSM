import ogr2osm

STREET_DIRECTIONS = {
    "N": "North ",
    "S": "South ",
    "E": "East ",
    "W": "West "
}

STREET_TYPES = {
    "AL": " Alley",
    "AV": " Avenue",
    "BL": " Boulevard",
    "CL": " Circle",
    "CM": " Common",
    "CT": " Court",
    "DR": " Drive",
    "EX": " Expressway",
    "FY": " Freeway",
    "HY": " Highway",
    "LN": " Lane",
    "LP": " Loop",
    "PL": " Place",
    "PY": " Parkway",
    "RD": " Road",
    "SQ": " Square",
    "ST": " Street",
    "TR": " Terrace",
    "WK": " Walkway",
    "WW": " Walkway",
    "WY": " Way",
    None: ""
}

class SantaClaraCountyParcelsTranslation(ogr2osm.TranslationBase):
    def filter_tags(self, ogrtags):
        return {
            "addr:housenumber": ogrtags["situs_house_number"]+ogrtags["situs_house_number_suffix"],
            "addr:street": STREET_DIRECTIONS.get(ogrtags["situs_street_direction"], "") + ogrtags["situs_street_name"].title() + STREET_TYPES[ogrtags["situs_street_type"]],
            "addr:unit": ogrtags["situs_unit_number"],
            "addr:city": ogrtags["situs_city_name"],
            "addr:state": ogrtags["situs_state_code"],
            "addr:postcode": ogrtags["situs_zip_code"]
        }
