import json, os, os.path
from urllib.request import urlopen
from urllib.parse import *
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

def parseServicesDirectory(url, j=None, path=None):
    if j is None: j = getJson(url)
    for service in j['services']:
        if service['type'] in ('MapServer', 'FeatureServer'):
            parseMapServer(urlAdd(url, service['name'].split('/')[-1], service['type']), path=service['name']+"_"+service['type'][0])
        else:
            warn("Unhandled service type "+service['type'])
    for folder in j['folders']:
        if path is None:
            p = folder
        else:
            p = os.path.join(path, folder)
        os.makedirs(p, exist_ok=True)
        parseServicesDirectory(urlAdd(url, folder.split('/')[-1]), path=p)

def parseMapServer(url, j=None, path=None):
    if j is None: j = getJson(url)
    if path is None and 'mapName' in j:
        path = j['mapName']
    print(path)
    if 'serviceDescription' in j:
        print(j['serviceDescription'])
    if path is not None:
        os.makedirs(path, exist_ok=True)
    for layer in j['layers']:
        name = layer['name'].replace(os.path.sep, '_')
        if 'parentLayerId' in layer:
            parentLayerId = layer['parentLayerId']
            while parentLayerId != -1:
                parents = [parent for parent in j['layers'] if parent['id'] == parentLayerId]
                name = os.path.join(parents[0]['name'].replace(os.path.sep, '_'), name)
                parentLayerId = parents[0]['parentLayerId']
            os.makedirs(os.path.split(name)[0], exist_ok=True)
        name = name+"_"+str(layer['id'])
        if path is None:
            p = name
        else:
            p = os.path.join(path, name)
        parseMapLayer(urlAdd(url, str(layer['id'])), path=p)

cellCount = 8

def parseMapLayer(url, j=None, path=None):
    if j is None: j = getJson(url)
    if path is None:
        path = j['name']
    print("   ", path)
    if 'description' in j:
        print("   ", j['description'])
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
            print("    Loading layer", j['name'], "section", xCell, "x", yCell)
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

def parseSomething(url, j=None):
    if j is None: j = getJson(url)
    if 'services' in j:
        parseServicesDirectory(url, j)
    elif 'layers' in j:
        parseMapServer(url, j)
    elif 'extent' in j:
        parseMapLayer(url, j)
    else:
        warn("Unhandled service with data "+repr(j)+" at "+url)

if __name__ == '__main__':
    import sys
    for url in sys.argv[1:]:
        parseSomething(url)

