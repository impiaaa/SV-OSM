import json, sys
from datetime import datetime, timedelta

print("Parsing GeoJSON", file=sys.stderr)
geojson = json.load(open(sys.argv[1]))
segments = {}
coordinates = {}
def getCoordId(coord):
    coord = tuple([round(c, 7) for c in coord])
    id = coordinates.get(coord, None)
    if id is None:
        id = len(coordinates)
        coordinates[coord] = id
    return id
featureProperties = []
print("Getting coordinates and segments", file=sys.stderr)
for featureId, feature in enumerate(geojson['features']):
    print(featureId, file=sys.stderr)
    featureProperties.append(feature['properties'])
    if feature['geometry']['type'] == "Polygon": polygons = [feature['geometry']['coordinates']]
    else:
        assert feature['geometry']['type'] == "MultiPolygon", feature['geometry']['type']
        polygons = feature['geometry']['coordinates']
    for polygon in polygons:
        for ring in polygon:
            assert ring[0] == ring[-1]
            for j, startCoord in enumerate(ring[:-1]):
                startCoordId = getCoordId(startCoord)
                endCoordId = getCoordId(ring[j+1])
                segmentFwd = (startCoordId, endCoordId)
                segmentRev = (endCoordId, startCoordId)
                if segmentFwd in segments: segments[segmentFwd].add(featureId)
                elif segmentRev in segments: segments[segmentRev].add(featureId)
                else:
                    if startCoord[0] < ring[j+1][0]:
                        segmentSort = (startCoordId, endCoordId)
                    elif startCoord[0] > ring[j+1][0]:
                        segmentSort = (endCoordId, startCoordId)
                    elif startCoord[1] < ring[j+1][1]:
                        segmentSort = (startCoordId, endCoordId)
                    else:
                        segmentSort = (endCoordId, startCoordId)
                    segments[segmentSort] = {featureId}
    #if featureId >= 300: break
del geojson
featureSets = {}
segments = list(segments.items())
print("Joining segments with common features", file=sys.stderr)
while len(segments):
    segment, featuresForSegment = segments.pop()
    featuresForSegment = tuple(sorted(featuresForSegment))
    if featuresForSegment in featureSets:
        featureSets[featuresForSegment].add(segment)
    else:
        featureSets[featuresForSegment] = {segment}
del segments
featureLines = {}
print("Joining lines", file=sys.stderr)
for featuresForSegment, segments in featureSets.items():
    segments = list(sorted(segments))
    lines = []
    for segment in segments:
        for line in lines:
            if line[-1] == segment[0]:
                line.append(segment[1])
                break
            elif line[0] == segment[1]:
                line.insert(0, segment[0])
                break
            elif line[-1] == segment[1]:
                line.append(segment[0])
                break
            elif line[0] == segment[0]:
                line.insert(0, segment[1])
                break
        else:
            lines.append(list(segment))
    featureLines[featuresForSegment] = lines
del featureSets

print("Output nodes", file=sys.stderr)

print("<?xml version='1.0' encoding='UTF-8'?>")
print("<osm version='0.6'>")
for (lon, lat), i in coordinates.items():
    print("  <node id='%d' visible='true' lat='%.7f' lon='%.7f' />"%(-1-i, lat, lon))
del coordinates

print("Output ways", file=sys.stderr)

featuresToLineIds = {}
allLines = []
i = 0
for featureIds, lines in featureLines.items():
    for line in lines:
        for featureId in featureIds:
            if featureId in featuresToLineIds: featuresToLineIds[featureId].add(i)
            else: featuresToLineIds[featureId] = {i}
        print("  <way id='%d' visible='true'>"%(-1-i))
        for node in line:
            print("    <nd ref='%d' />"%(-1-node))
        #print("    <tag k='license' v='Public domain' />")
        #print("    <tag k='source' v='City of San José: https://csj.maps.arcgis.com/apps/webappviewer/index.html?id=1dc3a4e02e654666b29c6928d8d8d04d' />")
        print("  </way>")
        allLines.append(line)
        i += 1

print("Sorting lines", file=sys.stderr)

featuresToLineIdsSorted = {}
for featureId, linesIds in featuresToLineIds.items():
    linesIdsSorted = []
    linesSorted = []
    while len(linesIds):
        lineId = linesIds.pop()
        line = allLines[lineId]
        for i in range(len(linesSorted)):
            if linesSorted[i][-1] == line[0]:
                linesSorted.insert(i+1, line)
                linesIdsSorted.insert(i+1, lineId)
                break
            elif linesSorted[i][0] == line[-1]:
                linesSorted.insert(i, line)
                linesIdsSorted.insert(i, lineId)
                break
            elif linesSorted[i][-1] == line[-1]:
                linesSorted.insert(i+1, line)
                linesIdsSorted.insert(i+1, lineId)
                break
            elif linesSorted[i][0] == line[0]:
                linesSorted.insert(i, line)
                linesIdsSorted.insert(i, lineId)
                break
        else:
            linesSorted.append(line)
            linesIdsSorted.append(lineId)
    featuresToLineIdsSorted[featureId] = linesIdsSorted

del featureLines, featuresToLineIds, allLines

print("Output relations", file=sys.stderr)

for featureId, lineIds in featuresToLineIdsSorted.items():
    print("  <relation id='%d' visible='true'>"%(-1-featureId))
    for lineId in lineIds:
        print("    <member type='way' ref='%d' role='' />"%(-1-lineId))
    print("    <tag k='admin_level' v='8' />")
    print("    <tag k='alt_name' v='San José' />")
    print("    <tag k='alt_name:en' v='San José' />")
    print("    <tag k='alt_name:vi' v='Xan Hô-xê;San José' />")
    print("    <tag k='border_type' v='city' />")
    print("    <tag k='boundary' v='administrative' />")
    print("    <tag k='license' v='Public domain' />")
    print("    <tag k='name' v='San Jose' />")
    print("    <tag k='name:am' v='ሳን ሆዜ' />")
    print("    <tag k='name:ar' v='سان خوسيه' />")
    print("    <tag k='name:en' v='San Jose' />")
    print("    <tag k='name:en-fonipa' v='ˌseən hoʊˈzeɪ' />")
    print("    <tag k='name:en:pronunciation' v='ˌseən hoʊˈzeɪ' />")
    print("    <tag k='name:es' v='San José' />")
    print("    <tag k='name:es-fonipa' v='ˌsan xoˈse' />")
    print("    <tag k='name:es:pronunciation' v='ˌsan xoˈse' />")
    print("    <tag k='name:gl' v='San Xosé' />")
    print("    <tag k='name:pronunciation' v='ˌseən hoʊˈzeɪ' />")
    print("    <tag k='name:vi' v='San Jose' />")
    print("    <tag k='name:vi-fonipa' v='saːn˧˧ ho˧˧ze˧˧' />")
    print("    <tag k='name:vi:pronunciation' v='saːn˧˧ ho˧˧ze˧˧' />")
    print("    <tag k='name:zh' v='聖荷西' />")
    print("    <tag k='name:zh-CN' v='圣何塞' />")
    print("    <tag k='name:zh-Hant' v='聖荷西' />")
    print("    <tag k='note' v='See https://wiki.openstreetmap.org/wiki/San_Jose,_California#Name regarding disputes about the name in English.' />")
    print("    <tag k='official_name' v='City of San José' />")
    print("    <tag k='source' v='City of San José: https://csj.maps.arcgis.com/apps/webappviewer/index.html?id=1dc3a4e02e654666b29c6928d8d8d04d' />")
    print("    <tag k='type' v='boundary' />")
    print("    <tag k='wikidata' v='Q16553' />")
    print("    <tag k='wikipedia' v='en:San Jose, California' />")
    startDate = datetime.fromisoformat(featureProperties[featureId]["ANNEXDATE"])+timedelta(hours=9)
    print("    <tag k='start_date' v='%s' />"%startDate.date().isoformat())
    endDate = featureProperties[featureId]["DISANNEXDATE"]
    if endDate is not None:
        endDate = datetime.fromisoformat(endDate)+timedelta(hours=9)
        print("    <tag k='end_date' v='%s' />"%endDate.date().isoformat())
    print("  </relation>")
print("</osm>")

