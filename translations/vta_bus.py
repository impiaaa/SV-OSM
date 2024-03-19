import ogr2osm
import csv
import osgeo.ogr

class VTABusInventoryTranslation(ogr2osm.TranslationBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gtfs_stops = {line["stop_code"]: line for line in csv.DictReader(open("gtfs_vta/stops.txt"))}


    def filter_feature(self, ogrfeature, layer_fields, reproject):
        stopid_field, = [index for index, field_name, field_type in layer_fields if field_name == "stopid"]
        stopid = ogrfeature.GetFieldAsString(stopid_field)
        gtfs_stop = self.gtfs_stops.get(stopid)
        if not gtfs_stop:
            return None
        geometry = osgeo.ogr.Geometry(osgeo.ogr.wkbPoint)
        geometry.AddPoint(float(gtfs_stop["stop_lon"]), float(gtfs_stop["stop_lat"]))
        ogrfeature.SetGeometry(geometry)
        return ogrfeature


    def filter_tags(self, ogrtags):
        osmtags = {
            "highway": "bus_stop",
            "public_transport": "platform",
            "bus": "yes",
            "network": "VTA",
            "network:wikidata": "Q1456861",
            "operator:wikidata": "Q1456861",
            "ref": ogrtags["stopid"],
            "gtfs:stop_code": ogrtags["stopid"],
        }
        if ogrtags["stopid_present"]:
            osmtags["ref:signed"] = ogrtags["stopid_present"]
        if ogrtags["bus_stop_pole"]:
            osmtags["pole"] = "no" if ogrtags["bus_stop_pole"] == "None" else "yes"
        if ogrtags["real_time_display"]:
            osmtags["passenger_information_display"] = "no" if ogrtags["real_time_display"] == "None" else "yes"
        if ogrtags["lighting_nearby"]:
            if "None" not in ogrtags["lighting_nearby"]:
                osmtags["lit"] = "yes"
            elif ogrtags["lighting_nearby"] == "None":
                osmtags["lit"] = "no"
        if ogrtags["bench"]:
            osmtags["bench"] = ogrtags["bench"]
        if ogrtags["wood_ad_bench"]:
            osmtags["advertising"] = "yes" if ogrtags["wood_ad_bench"] != "0" else "no"
        if ogrtags["trashcan"]:
            osmtags["bin"] = ogrtags["trashcan"]
        if ogrtags["shelter_present"]:
            osmtags["shelter"] = ogrtags["shelter_present"]
        if ogrtags["ad_present"] and osmtags.get("advertising") != "yes":
            osmtags["advertising"] = ogrtags["ad_present"]

        gtfs_stop = self.gtfs_stops[ogrtags["stopid"]]
        if gtfs_stop["stop_name"]:
            osmtags["name"] = gtfs_stop["stop_name"]
        if gtfs_stop["stop_desc"]:
            osmtags["description"] = gtfs_stop["stop_desc"]
        if gtfs_stop["stop_url"]:
            osmtags["website"] = gtfs_stop["stop_url"]
        if gtfs_stop["wheelchair_boarding"] in ("1", "2"):
            osmtags["wheelchair"] = "yes" if gtfs_stop["wheelchair_boarding"] == "1" else "no"
        if gtfs_stop["platform_code"]:
            osmtags["local_ref"] = gtfs_stop["platform_code"]
        return osmtags

    def merge_tags(self, geometry_type, tags_existing_geometry, tags_new_geometry):
        return {k: v for k, v in tags_existing_geometry.items() if len(v) == 1}

