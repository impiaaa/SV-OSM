import sys, os
from osgeo import ogr

ogr.UseExceptions()

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = os.getcwd()

dataSource = ogr.Open(path, 0)

layerFields = {}

for i in range(dataSource.GetLayerCount()):
    layer = dataSource.GetLayer(i)
    featureDefinition = layer.GetLayerDefn()
    print("Layer:", featureDefinition.GetName())
    layer.ResetReading()

    fieldNames = [featureDefinition.GetFieldDefn(j).GetNameRef() for j in range(featureDefinition.GetFieldCount())]
    #fieldAliases = {featureDefinition.GetFieldDefn(j).GetNameRef(): featureDefinition.GetFieldDefn(j).GetComment() for j in range(featureDefinition.GetFieldCount())}
    layerFields[layer.GetName()] = set(fieldNames)
    fieldValues = [set() for f in fieldNames]
    fieldHasEmpty = [False for f in fieldNames]

    for j in range(layer.GetFeatureCount()):
        ogrfeature = layer.GetNextFeature()
        if ogrfeature is None: continue
        
        processedFields = 0
        for k in range(len(fieldNames)):
            if fieldHasEmpty[k] and isinstance(fieldValues[k], str):
                continue
            
            value = ogrfeature.GetFieldAsString(k)
            
            if value == "":
                fieldHasEmpty[k] = True
            
            elif isinstance(fieldValues[k], set):
                if len(fieldValues[k]) >= 20:
                    fieldValues[k] = value
                else:
                    fieldValues[k].add(value)
            
            processedFields += 1
        
        if processedFields == 0:
            break
    
    for (fieldName, values, hasEmpty) in zip(fieldNames, fieldValues, fieldHasEmpty):
        print("   ", fieldName, end=' ')
        if hasEmpty:
            if len(values) == 0:
                print("is always empty")
                continue
            print("can be", end=' ')
        else:
            print("is never", end=' ')
        print("empty, has", end=' ')
        if isinstance(values, str):
            print("many values, for example,", values)
        else:
            print("values:")
            for v in values:
                print("       ", v)
            print()

for layerName, fieldNames in layerFields.items():
    identifyingFields = set(fieldNames)
    for otherName, otherFields in layerFields.items():
        if otherName != layerName:
            identifyingFields.difference_update(otherFields)
    print(layerName, "has identifying fields", ", ".join(identifyingFields))

