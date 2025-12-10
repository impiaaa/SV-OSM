import json, os, os.path
from urllib.request import urlopen
from urllib.parse import *
import urllib
from warnings import warn

def getJson(url):
    u = urlparse(url)
    q = parse_qs(u.query)
    q['f'] = 'json'
    url = urlunparse(u._replace(query=urlencode(q)))
    #print("Loading", url)
    return json.load(urlopen(url))

def urlAdd(base, *components):
    u = urlparse(base)
    return urlunparse(u._replace(path=u.path+'/'+'/'.join(components)))

def parseServicesDirectory(url, j=None, path=None, indent=0):
    try:
        if j is None:
            j = getJson(url)
    except urllib.error.HTTPError as e:
        print('  '*indent, e)
        return
    for service in j.get('services', []):
        if service['type'] in ('MapServer', 'FeatureServer'):
            parseMapServer(urlAdd(url, service['name'].split('/')[-1], service['type']), path=service['name']+"_"+service['type'][0], indent=indent)
        else:
            warn("Unhandled service type "+service['type'])
    for folder in j.get('folders', []):
        if path is None:
            p = folder
        else:
            p = os.path.join(path, folder)
        #os.makedirs(p, exist_ok=True)
        parseServicesDirectory(urlAdd(url, folder.split('/')[-1]), path=p, indent=indent+1)

def parseMapServer(url, j=None, path=None, indent=0):
    try:
        if j is None:
            j = getJson(url)
    except urllib.error.HTTPError as e:
        print('  '*indent, e)
        return
    if path is None and 'mapName' in j:
        path = j['mapName']
    print('  '*indent, path)
    if 'serviceDescription' in j:
        print('  '*indent, j['serviceDescription'])
    #if path is not None:
    #    os.makedirs(path, exist_ok=True)
    for layer in j['layers']:
        if layer.get("type") != "Feature Layer": continue
        name = layer['name'].replace(os.path.sep, '_')
        if 'parentLayerId' in layer:
            parentLayerId = layer['parentLayerId']
            while parentLayerId != -1:
                parents = [parent for parent in j['layers'] if parent['id'] == parentLayerId]
                name = os.path.join(parents[0]['name'].replace(os.path.sep, '_'), name)
                parentLayerId = parents[0]['parentLayerId']
            parentdir = os.path.split(name)[0]
            #if parentdir:
            #    os.makedirs(parentdir, exist_ok=True)
        name = name+"_"+str(layer['id'])
        if path is None:
            p = name
        else:
            p = os.path.join(path, name)
        parseMapLayer(urlAdd(url, str(layer['id'])), path=p, indent=indent+1)

cellCount = 8
def isDateField(field):
    return field["type"] == "esriFieldTypeDate" and field["name"] not in ("LASTUPDATE", "CREATIONDATE")

def parseMapLayer(url, j=None, path=None, indent=0):
    try:
        if j is None:
            j = getJson(url)
    except urllib.error.HTTPError as e:
        print('  '*indent, e)
        return
    if path is None:
        path = j['name']
    if not any(isDateField(field) for field in j.get("fields", [])): return
    print('  '*indent, path)
    #if 'description' in j:
    #    print('  '*indent, j['description'])
    for field in j.get("fields", []):
        if isDateField(field):
            print('  '*(indent+1), field.get("name"), field.get("alias"))
    return
    if os.path.exists(path+'.geojson'): return
    extent = j['extent']
    xSize = extent['xmax']-extent['xmin']
    ySize = extent['ymax']-extent['ymin']
    subExtent = extent.copy()
    u = urlparse(url)
    u = u._replace(path=u.path+'/query')
    q = {'f': 'geojson',
         'returnGeometry': 'true',
         'spatialRel': 'esriSpatialRelIntersects',
         'geometryType': 'esriGeometryEnvelope',
         'outFields': '*'}
    features = []
    lastPiece = None
    for yCell in range(cellCount):
        subExtent['ymin'] = extent['ymin'] + ySize*yCell/cellCount
        subExtent['ymax'] = extent['ymin'] + ySize*(yCell+1)/cellCount
        for xCell in range(cellCount):
            subExtent['xmin'] = extent['xmin'] + xSize*xCell/cellCount
            subExtent['xmax'] = extent['xmin'] + xSize*(xCell+1)/cellCount
            q['geometry'] = json.dumps(subExtent)
            print('  '*indent, "Loading layer", j['name'], "section", xCell, "x", yCell)
            layerPiece = json.load(urlopen(urlunparse(u._replace(query=urlencode(q)))))
            if 'features' not in layerPiece:
                warn("Layer part "+repr(layerPiece)+" has no features")
                continue
            pieceFeatures = layerPiece.pop('features')
            if lastPiece is None or layerPiece == lastPiece:
                features.extend(pieceFeatures)
                lastPiece = layerPiece
            else:
                warn("Layer part info "+repr(layerPiece)+" doesn't match that of other parts "+repr(lastPiece))
    if lastPiece is None:
        warn("Layer "+path+" entirely empty")
    else:
        geojson = {'features': features}
        geojson.update(lastPiece)
        json.dump(geojson, open(path+'.geojson', 'w'))

def parseSomething(url, j=None, indent=0):
    try:
        if j is None:
            j = getJson(url)
    except urllib.error.HTTPError as e:
        print('  '*indent, e)
        return
    if 'services' in j:
        parseServicesDirectory(url, j, indent=indent+1)
    elif 'layers' in j:
        parseMapServer(url, j, indent=indent+1)
    elif 'extent' in j:
        parseMapLayer(url, j, indent=indent+1)
    else:
        warn("Unhandled service with data "+repr(j)+" at "+url)

if __name__ == '__main__':
    import sys
    for url in sys.argv[1:]:
        parseSomething(url)

