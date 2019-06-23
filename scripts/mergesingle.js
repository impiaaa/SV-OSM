function go() {
    var console = require("josm/scriptingconsole");
    var layers = require("josm/layers");
    var command = require("josm/command");
    var layer = layers.activeLayer;
    var data = layer.data;
    var relations = data.getRelations();
    console.println(relations.size() + " relations");
    var merged = 0;
    for (var it = relations.iterator(); it.hasNext();) {
        var relation = it.next();
        if (relation.getMembersCount() == 1) {
            if (relation.firstMember().isRelation()) {
                console.println("skipping deeper relation " + relation.firstMember().getUniqueId() + " in " + relation.getId());
            }
            var member = relation.firstMember().getMember();
            layer.apply(
                command.change(member, {tags: relation.tags}),
                command.delete(relation)
            );
            merged++;
        }
    }
    console.println("merged " + merged + " relations");
}
go();

