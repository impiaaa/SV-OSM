var equatorialRadius = 6378137.0;
var polarRadius = 6356752.3;
var e = Math.sqrt(1.0 - (polarRadius*polarRadius)/(equatorialRadius*equatorialRadius));

function primeVerticalRadius(lat) {
    var s = Math.sin(lat);
    return equatorialRadius/Math.sqrt(1.0 - e*e*s*s);
}

function geoToECEF(geo) {
    var l = geo.lon*Math.PI/180.0;
    var t = geo.lat*Math.PI/180.0;
    var ct = Math.cos(t);
    var n = primeVerticalRadius(t);
    return {
        x: n * ct * Math.cos(l),
        y: n * ct * Math.sin(l),
        z: (((polarRadius*polarRadius)/(equatorialRadius*equatorialRadius))*n)*Math.sin(t)
    };
}

function multMat(a, b) {
    var rows = a.length;
    var columns = b[0].length;
    var units = b.length;
    var result = new Array(rows);
    for (var row = 0; row < rows; row++) {
        result[row] = new Array(columns);
        for (var column = 0; column < columns; column++) {
            result[row][column] = 0.0;
            for (var unit = 0; unit < b.length; unit++) {
                result[row][column] += a[row][unit]*b[unit][column];
            }
        }
    }
    return result;
}

function geoToENU(focus, ref) {
    var ecefFoc = geoToECEF(focus);
    var ecefRef = geoToECEF(ref);
    var l = ref.lon*Math.PI/180.0;
    var sl = Math.sin(l);
    var cl = Math.cos(l);
    var t = ref.lat*Math.PI/180.0;
    var st = Math.sin(t);
    var ct = Math.cos(t);
    var mat = [[   -sl,     cl,  0],
               [-st*cl, -st*sl, ct],
               [ ct*cl,  ct*sl, st]];
    var vec = [[ecefFoc.x - ecefRef.x], [ecefFoc.y - ecefRef.y], [ecefFoc.z - ecefRef.z]];
    var enu = multMat(mat, vec);
    return {x: enu[0][0], y: enu[1][0], z: enu[2][0]};
}

function ECEFToGeo(ecef) {
    var r = Math.sqrt(ecef.x*ecef.x + ecef.y*ecef.y);
    var ep2 = (equatorialRadius*equatorialRadius - polarRadius*polarRadius)/(polarRadius*polarRadius);
    var F = 54.0*polarRadius*polarRadius*ecef.z*ecef.z;
    var G = r*r + (1.0 - e*e)*ecef.z*ecef.z - e*e*(equatorialRadius*equatorialRadius - polarRadius*polarRadius);
    var c = (e*e*e*e*F*r*r)/(G*G*G);
    var s = Math.cbrt(1.0 + c + Math.sqrt(c*c + 2.0*c));
    var P = F/(3.0*Math.pow(s + 1.0/s + 1.0, 2)*G*G);
    var Q = Math.sqrt(1.0 + 2.0*Math.pow(e, 4)*P);
    var r0 = -(P*e*e*r)/(1+Q) + Math.sqrt(0.5*equatorialRadius*equatorialRadius*(1 + 1/Q) - (P*(1-e*e)*ecef.z*ecef.z)/(Q*(1+Q)) - 0.5*P*r*r);
    var U = Math.sqrt(Math.pow(r - e*e*r0, 2) + ecef.z*ecef.z);
    var V = Math.sqrt(Math.pow(r - e*e*r0, 2) + (1 - e*e)*ecef.z*ecef.z);
    var z0 = (polarRadius*polarRadius*ecef.z)/(equatorialRadius*V);
    return {h: U*(1.0 - (polarRadius*polarRadius)/(equatorialRadius*V)),
            lat: Math.atan((ecef.z + ep2*z0)/r)*180.0/Math.PI,
            lon: Math.atan2(ecef.y, ecef.x)*180.0/Math.PI};
}

function ENUToGeo(focusLocal, ref) {
    var l = ref.lon*Math.PI/180.0;
    var sl = Math.sin(l);
    var cl = Math.cos(l);
    var t = ref.lat*Math.PI/180.0;
    var st = Math.sin(t);
    var ct = Math.cos(t);
    var mat = [[-sl, -st*cl, ct*cl],
               [ cl, -st*sl, ct*sl],
               [  0,  ct,    st]];
    var vec = [[focusLocal.x], [focusLocal.y], [focusLocal.z]];
    var v = multMat(mat, vec);
    var refEcef = geoToECEF(ref);
    var focusEcef = {x: v[0][0] + refEcef.x, y: v[1][0] + refEcef.y, z: v[2][0] + refEcef.z};
    return ECEFToGeo(focusEcef);
}

function go() {
    var console = require("josm/scriptingconsole");
    var layers = require("josm/layers");
    var command = require("josm/command");
    var maxAmt = 20.0;
    var layer = layers.activeLayer;
    var data = layer.data;
    var ways = data.getSelectedWays();
    console.println(ways.size() + " ways");
    var changes = new Array();
    for (var it = ways.iterator(); it.hasNext();) {
        var way = it.next();
        if (!way.isArea()) {
            console.println("Way " + way.getId() + " is not area");
            continue;
        }
        
        var bbox = new org.openstreetmap.josm.data.osm.BBox(way.getBBox());
        bbox.add(bbox.getTopLeftLon()-0.001, bbox.getBottomRightLat()-0.001);
        bbox.add(bbox.getBottomRightLon()+0.001, bbox.getTopLeftLat()+0.001);
        var nearbyNodes = data.$searchNodes(bbox);
        var nearbyWays = new java.util.HashSet();
        for (var i = 0; i < nearbyNodes.size(); i++) {
            nearbyWays.addAll(nearbyNodes.get(i).getParentWays());
        }
        nearbyWays.remove(way);
        nearbyWays = nearbyWays.toArray();
        
        var nodesCount = way.getNodesCount();
        console.println("Processing way " + way.getId() + " with " + nodesCount + " nodes");
        for (var i = 0; i < nodesCount-1; i++) {
            var middle = way.getNode(i);
            if (middle.getParentWays().size() != 1) {
                continue;
            }
            var prev = way.getNode(i == 0 ? nodesCount - 2 : i - 1);
            var next = way.getNode((i + 1) % nodesCount);
            
            var amt = maxAmt;
            for (var j = 0; j < nearbyWays.length; j++) {
                var way2 = nearbyWays[j];
                var dist = org.openstreetmap.josm.tools.Geometry.getDistanceWayNode(way2, middle);
                if (dist > 0 && dist/2 < amt) {
                    amt = dist/2;
                }
            }
            
            var prevLocal = geoToENU(prev.pos, middle.pos);
            var nextLocal = geoToENU(next.pos, middle.pos);
            // middle local is 0,0
            var normal = {x: prevLocal.y - nextLocal.y, y: nextLocal.x - prevLocal.x};
            var len = Math.sqrt(normal.x*normal.x + normal.y*normal.y);
            normal.x /= len;
            normal.y /= len;
            var newPosLocal = {x: normal.x * amt, y: normal.y * amt, z: 0.0}; // close enough
            var newPosGeo = ENUToGeo(newPosLocal, middle.pos);
            changes.push(command.change(middle, newPosGeo));
        }
    }
    layer.apply.apply(layer, changes);
}
go();

