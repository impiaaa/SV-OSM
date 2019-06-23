function fixAce() {
    var console = require("josm/scriptingconsole");
    var layers = require("josm/layers");
    var command = require("josm/command");
    
    var real = layers.get("VTA enclosing.osm");

    var relations = real.data.query(function(p) {
        return p.isRelation &&
               p.has("route") &&
               !p.has("ref:VTA") &&
               !p.has("ref:vta") &&
               p.has("ref") &&
               p.get("network") == "VTA" &&
               !p.get("ref").match(/[0-9]/);
    });
    var fixed = 0;
    for (i = 0; i < relations.length; i++) {
        var name = relations[i].get("name");
        if (!name) {
            continue;
        }
        var match = name.match(/^VTA ([0-9]+) ACE/);
        if (!match) {
            continue;
        }
        var ref = match[1];
        real.apply(command.change(relations[i], {"tags": {"ref:VTA": ref}}));
        fixed++;
    }
    java.lang.System.out.println("fixed " + fixed + " ACE refs\n");
    console.println("fixed " + fixed + " ACE refs\n");
}
fixAce();

function doRoutes() {
    var console = require("josm/scriptingconsole");
    var layers = require("josm/layers");
    var RelationBuilder = require("josm/builder").RelationBuilder;
    var command = require("josm/command");
    
    function log(x) {
        java.lang.System.out.println(x);
        console.println(x);
    }
    
    var vta = layers.get("Bus_fix4.osm");
    var real = layers.get("VTA enclosing.osm");
    
    var ways = vta.data.query(function(p) {
        return p.isWay && p.has("route") && p.get("type") == "route";
    });
    log("route ways: " + ways.length);
    
    var newRelations = 0;
    var mergedRelations = 0;
    
    for (i = 0; i < ways.length; i++) {
        var way = ways[i];
        
        var relations = real.data.query(function(p) {
            return p.isRelation &&
                   p.has("route") &&
                   (p.get("ref:VTA") == way.get("ref") ||
                    p.get("ref:vta") == way.get("ref") ||
                    ((p.get("network") == "VTA" ||
                      p.get("operator") == "VTA") &&
                     p.get("ref") == way.get("ref"))) &&
                   p.get("type") == "route" &&
                   //(p.get("from") == way.get("from")) &&
                   p.get("to") == way.get("to") &&
                   (!p.has("vta:pattern") || p.get("vta:pattern") == way.get("vta:pattern"));
        });
        
        var relation = null;
        if (relations.length == 0) {
            log("creating " + way.get("name"));
            relation = RelationBuilder.create({tags: way.tags});
            real.apply(command.add(relation));
            //vta.apply(command.delete(way));
            newRelations++;
        }
        else {
            if (relations.length == 1) {
                log("only found one relation for " + way.get("name"));
                relation = relations[0];
                
                // create duplicate for opposite direction
                if (0){//(!relation.has("from") || !relation.has("to")) {
                    log("creating " + way.get("name"));
                    var relation2 = RelationBuilder.create({tags: relation.tags, members: relation.members});
                    relation2.tags["from"] = null;
                    relation2.tags["to"] = null;
                    real.apply(command.add(relation2));
                    newRelations++;
                }
            }
            else {
                log(way.get("name") + " has " + relations.length + " ambiguous matches, skipping");
                continue;
            }
            
            var newTags = {};
            for (k = 0; k < way.keys.length; k++) {
                var tag = way.keys[k];
                newTags[tag] = way.tags[tag];
            }
            // prefer existing tags
            for (k = 0; k < relation.keys.length; k++) {
                tag = relation.keys[k];
                newTags[tag] = relation.tags[tag];
            }
            
            real.apply(command.change(relation, {"tags": newTags}));
            //vta.apply(command.delete(way));
            
            mergedRelations++;
        }
        
        var followNodes = [];
        var lastNodes = null;
        for (j = 0; j < way.nodes.length-1; j++) {
            var pt1 = way.nodes[j];
            var pt2 = way.nodes[j+1];
            var box = new org.openstreetmap.josm.data.Bounds(
                Math.min(pt1.lat, pt2.lat)-0.0003,
                Math.min(pt1.lon, pt2.lon)-0.0003,
                Math.max(pt1.lat, pt2.lat)+0.0003,
                Math.max(pt1.lon, pt2.lon)+0.0003
            ).toBBox();
            var innerNodes = real.data.$searchNodes(box);
            for (k = 0; k < innerNodes.size(); k++) {
                var innerNode = innerNodes.get(k);
                if (org.openstreetmap.josm.tools.Geometry.getDistanceWayNode(way, innerNode) < 10 &&
                    (lastNodes == null || !lastNodes.contains(innerNode))) {
                    followNodes.push(innerNode);
                }
            }
            lastNodes = innerNodes;
        }
        //log("found " + followNodes.length + " nodes along way");
        var members = [];
        var lastWays = null;
        for (j = 0; j < followNodes.length; j++) {
            var theseWays = followNodes[j].getParentWays();
            if (lastWays && lastWays != theseWays) {
                for (k = 0; k < lastWays.size(); k++) {
                    for (l = 0; l < theseWays.size(); l++) {
                        if (lastWays.get(k) == theseWays.get(l) &&
                            (members.length == 0 || members[members.length-1].getMember() != lastWays.get(k))) {
                            members.push(RelationBuilder.member("", lastWays.get(k)));
                        }
                    }
                }
            }
            if (theseWays.size() > 0) {
                lastWays = theseWays;
            }
            /*else if (followNodes[j].has("route_ref") && followNodes[j].get("route_ref").indexOf(relation.get("ref")) != -1) {
                members.push(RelationBuilder.member("platform", followNodes[j]));
            }*/
        }
        log("adding " + members.length + " members");
        real.apply(command.change(relation, {"members": members}));
    }
    
    log("created " + newRelations + " relations");
    log("merged " + mergedRelations + " relations");
    log("");
}
doRoutes();

function indexOf(ls, thing) {
    for (var h = 0; h < ls.length; h++) {
        if (ls[h] == thing) {
            return h;
        }
    }
    return -1;
}

function toTitleCase(s) {
    var re = /[a-z]+[^a-z]*/gi;
    var t = "";
    var match = s.match(re);
    for (hdgdfhgfd = 0; hdgdfhgfd < match.length; hdgdfhgfd++){
        t += match[hdgdfhgfd][0].toUpperCase();
        t += match[hdgdfhgfd].substr(1, match[hdgdfhgfd].length-1).toLowerCase();
    }
    return t;
}

function makeMasterRelations() {
    var console = require("josm/scriptingconsole");
    var layers = require("josm/layers");
    var RelationBuilder = require("josm/builder").RelationBuilder;
    var command = require("josm/command");
    
    function log(x) {
        java.lang.System.out.println(x);
        console.println(x);
    }
    
    var real = layers.get("VTA enclosing.osm");
    
    var routes = real.data.query(function(p) {
        return p.isRelation &&
               p.has("route") &&
               p.get("type") == "route";
    });
    log("routes: " + routes.length);
    
    var refs = [];
    for (i = 0; i < routes.length; i++) {
        var ref = routes[i].get("vta:lineabbr");
        if (!ref) {
            continue;
        }
        if (indexOf(refs, ref) == -1) {
            refs.push(ref);
        }
    }
    
    var masters = real.data.query(function(p) {
        return p.isRelation &&
               p.has("route_master") &&
               p.get("type") == "route_master";
    });
    log("route_masters: " + masters.length);
    
    for (i = 0; i < masters.length; i++) {
        var ref = null;
        if (masters[i].has("ref:VTA")) {
            ref = masters[i].get("ref:VTA");
        }
        else if (masters[i].has("ref:vta")) {
            ref = masters[i].get("ref:vta");
        }
        else if (masters[i].has("ref") && (masters[i].get("network") == "VTA" || masters[i].get("operator") == "VTA")) {
            ref = masters[i].get("ref");
        }
        if (ref) {
            var idx = indexOf(refs, ref);
            if (idx != -1) {
                refs.splice(idx, 1);
            }
        }
    }
    
    log("refs: " + refs.length);
    
    for (i = 0; i < refs.length; i++) {
        var ref = refs[i];
        log("making master for ref " + ref);
        routes = real.data.query(function(p) {
            return p.isRelation &&
                   p.has("route") &&
                   (p.get("vta:lineabbr") == ref/* ||
                    p.get("ref:VTA") == ref ||
                    p.get("ref:vta") == ref ||
                    ((p.get("network") == "VTA" ||
                      p.get("operator") == "VTA") &&
                     p.get("ref") == ref)*/) &&
                   p.get("type") == "route";
        });
        
        var members = [];
        for (j = 0; j < routes.length; j++) {
            members.push(RelationBuilder.member("", routes[j]));
        }
        
        var commonTags = {};
        for (j = 0; j < routes[0].keys.length; j++) {
            commonTags[routes[0].keys[j]] = routes[0].tags[routes[0].keys[j]];
        }
        for (j = 1; j < routes.length; j++) {
            for (k = 0; k < routes[j].keys.length; k++) {
                var key = routes[j].keys[k];
                if (!key) {
                    continue;
                }
                var val = routes[j].tags[key];
                if (!val) {
                    continue;
                }
                if (commonTags.hasOwnProperty(key) && commonTags[key] != val) {
                    delete commonTags[key];
                }
            }
            for (var commProp in commonTags) {
                if (!commProp) {
                    continue;
                }
                var val = commonTags[commProp];
                if (!val) {
                    continue;
                }
                if (routes[j].keys.indexOf(commProp) != -1 || routes[j].tags[commProp] != val) {
                    delete commonTags[commProp];
                }
            }
        }
        
        log(members.length + " members, " + Object.keys(commonTags).length + " common tags");
        
        commonTags["type"] = "route_master";
        commonTags["route_master"] = routes[0].tags["route"];
        commonTags["name"] = "VTA " + ref;
        commonTags["official_name"] = toTitleCase(commonTags["vta:linename"]);
        delete commonTags["route"];
        
        var relation = RelationBuilder.create({members: members, tags: commonTags});
        real.apply(command.add(relation));
    }
}
makeMasterRelations();

