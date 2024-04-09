# ogr2ogr -overwrite --debug on -f PostgreSQL -progress -nlt MULTIPOLYGON -dim XY -nln los_gatos_buildings -oo tile_extension="pbf?cacheKey=b4adae4b97bfcaad" -oo metadata_file="los_gatos_metadata.json" "PG:dbname=osm" "MVT:http://localhost:8000/16"
import http.server
class RedirHandler(http.server.BaseHTTPRequestHandler):
    baseurl = "https://tiles.arcgis.com/tiles/JAU7IM34hqT9y9ew/arcgis/rest/services/BuildingsVTG/VectorTileServer/tile"
    urlformat = "{base}/{z}/{y}/{x}.{ext}"
    def do_GET(self):
        if '.' in self.path and self.path.count('/') == 3:
            path, ext = self.path.split('.')
            blank, z, x, y = path.split('/')
            url = self.urlformat.format(base=self.baseurl, x=x, y=y, z=z, ext=ext)
        else:
            url = self.baseurl+self.path
        self.send_response(302)
        self.send_header("Location", url)
        self.log_message("Redirecting to %s", url)
        self.end_headers()

httpd = http.server.HTTPServer(('', 8000), RedirHandler)
httpd.serve_forever()
