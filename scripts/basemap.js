function containsNode(thing, node) {
    if (thing.isWay) {
        return org.openstreetmap.josm.tools.Geometry.nodeInsidePolygon(node, thing.getNodes());
    }
    else if (thing.isRelation) {
        return org.openstreetmap.josm.tools.Geometry.isNodeInsideMultiPolygon(node, thing, null);
    }
    else {
        return false;
    }
}

function containsWay(thing, way) {
    if (thing.isWay) {
        return org.openstreetmap.josm.tools.Geometry.polygonIntersection(way.getNodes(), thing.getNodes());
    }
    else if (thing.isRelation) {
        return org.openstreetmap.josm.tools.Geometry.isPolygonInsideMultiPolygon(way.getNodes(), thing, null) ?
            org.openstreetmap.josm.tools.Geometry.PolygonIntersection.FIRST_INSIDE_SECOND :
            org.openstreetmap.josm.tools.Geometry.PolygonIntersection.OUTSIDE;
    }
    else {
        return false;
    }
}

function mergeParcels() {
    var console = require("josm/scriptingconsole");
    var command = require("josm/command");
    var layers = require("josm/layers");
    
    var layer = layers.get("Basemap2.osm");
    var ds = layer.data;
    
    var parcels = layers.get("Basemap.osm").data.query(function(p) {
        return !p.isNode && p.has("sjc:ParcelID") && !p.has("building");
    });
    console.println("number of parcels: " + parcels.length);
    java.lang.System.out.println("number of parcels: " + parcels.length);
    
    var merged = 0;
    for (i = 0; i < parcels.length; i++) {
        var parcel = parcels[i];
        var pid = parcel.get("sjc:ParcelID");
        if (i%200 == 0) java.lang.System.out.println("Parcel no. " + i + " ID " + pid);
        //console.println("Parcel no. " + i + " ID " + pid);
        
        var innerWays = ds.searchWays(parcel.getBBox());
        //java.lang.System.out.println(innerWays.size() + " ways inside");
        //console.println(innerWays.size() + " ways inside");
        var buildingWays = [];
        for (j = 0; j < innerWays.size(); j++) {
            var way = innerWays.get(j);
            if (way.has("building") && !way.has("sjc:ParcelID") && !way.isDeleted) {
                var result = containsWay(parcel, way);
                if (result == org.openstreetmap.josm.tools.Geometry.PolygonIntersection.FIRST_INSIDE_SECOND) {
                    buildingWays.push(way);
                }
                else if (result == org.openstreetmap.josm.tools.Geometry.PolygonIntersection.CROSSING) {
                    buildingWays.splice(0);
                    break;
                }
            }
        }
        if (buildingWays.length == 0) {
            continue;
        }
        
        var innerNodes = ds.searchNodes(parcel.getBBox());
        //java.lang.System.out.println(innerNodes.size() + " nodes inside");
        //console.println(innerNodes.size() + " nodes inside");
        var buildingNodes = [];
        for (j = 0; j < innerNodes.size(); j++) {
            var node = innerNodes.get(j);
            if (node.has("building") && node.get("sjc:ParcelID") == pid && !node.isDeleted && containsNode(parcel, node)) {
                buildingNodes.push(node);
            }
        }
        if (buildingNodes.length != 1) {
            continue;
        }
        
        var addrNode = buildingNodes[0];
        buildingWays.sort(function(a, b) {
            return org.openstreetmap.josm.tools.Geometry.closedWayArea(b) - org.openstreetmap.josm.tools.Geometry.closedWayArea(a);
        });
        var building = buildingWays[0];
        layer.apply(
            // copy tags from node to way
            command.change(building, {tags: addrNode.tags}),
            // delete node
            command.delete(addrNode)
        );
        merged++;
        building.setModified(true);
        //parcel.set(nodes[0].tags);
        //ds.remove(nodes[0].id, "node");
    }
    console.println("merged " + merged);
}
mergeParcels();

