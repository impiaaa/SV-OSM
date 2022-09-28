from xml.dom import minidom

print("parsing")
doc = minidom.parse("ohm6.osm")

print("getting ways")
ways = doc.getElementsByTagName("way")

print("finding dupes in", len(ways), "ways")
duplicateWays = {}
for i, way in enumerate(ways):
    if len(way.getElementsByTagName("tag")) > 0: continue
    print(i, end=' ', flush=True)
    refs = tuple([int(nd.getAttribute("ref")) for nd in way.getElementsByTagName("nd")])
    if tuple(reversed(refs)) in duplicateWays: refs = tuple(reversed(refs))
    myId = int(way.getAttribute("id"))
    if refs in duplicateWays: duplicateWays[refs].add(myId)
    else: duplicateWays[refs] = {myId}

print()
duplicateWays = list([wayIds for wayIds in duplicateWays.values() if len(wayIds) > 1])
print(len(duplicateWays), "duplicate sets")

if len(duplicateWays) > 0:
    print("getting relations")
    relations = doc.getElementsByTagName("relation")

    print("scanning", len(relations), "relations")
    for i, relation in enumerate(relations):
        print(i, end=' ', flush=True)
        for wayIds in duplicateWays:
            assert len(wayIds) > 1
            replacementId = min({wayId for wayId in wayIds if wayId > 0})
            wayIds = {wayId for wayId in wayIds if wayId != replacementId}
            assert len(wayIds) > 0
            for member in relation.getElementsByTagName("member"):
                if member.getAttribute("type") == "way" and int(member.getAttribute("ref")) in wayIds:
                    member.setAttribute("ref", str(replacementId))
                    relation.setAttribute("action", "modify")

    print()
    print("writing")
    out = open("ohm7.osm", 'w')
    doc.writexml(out)
    out.close()

