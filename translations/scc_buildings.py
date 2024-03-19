import ogr2osm

def convertHeight(h):
    return "%.2f"%round(float(h)*0.3048, 2)

class SantaClaraCountyBuildingsFootprints2DTranslation(ogr2osm.TranslationBase):
    def filter_tags(self, ogrtags):
        return {
            "building": "yes",
            "ele": convertHeight(ogrtags["base_heigh"]),
            "height": convertHeight(ogrtags["building_h"])
        }
