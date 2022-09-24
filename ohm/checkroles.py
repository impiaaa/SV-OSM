from xml.dom import minidom
l = []
for relation in minidom.parse(open('san jose annexations uniq.osm')).getElementsByTagName("osm")[0].getElementsByTagName("relation"):
    members = relation.getElementsByTagName("member")
    if any([m.getAttribute('role') == '' for m in members]):
        l.append(len(members))
l.sort()
for m in l: print(m)

