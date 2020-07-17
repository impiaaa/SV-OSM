from qgis.core import QgsProject
from qgis import processing
zparts = QgsProject.instance().mapLayersByName("zoning parts")[0]
merged = QgsProject.instance().mapLayersByName("trim")[0]
layer = None
for i in range(1, 3511):
    print(i)
    zparts.selectByExpression("grouping=%d"%i)
    merged.selectByExpression("id=%d"%i)
    result = processing.run("qgis:snapgeometries", {'INPUT': QgsProcessingFeatureSourceDefinition(merged.name(), True), 'REFERENCE_LAYER': QgsProcessingFeatureSourceDefinition(zparts.name(), True), 'TOLERANCE': 200, 'BEHAVIOR': 2, 'OUTPUT': "memory:"})
    if layer is None:
        layer = result['OUTPUT']
    else:
        layer.dataProvider().addFeatures(result['OUTPUT'].getFeatures())

