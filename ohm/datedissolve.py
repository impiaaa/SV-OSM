# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant, QDateTime
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsField,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterField,
                       QgsExpression,
                       QgsFeatureRequest,
                       QgsVectorLayer,
                       QgsFeature,
                       QgsMultiPolygon)
from qgis import processing


class DateDissolve(QgsProcessingAlgorithm):
    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    STARTDATEFIELD = 'STARTDATEFIELD'
    ENDDATEFIELD = 'ENDDATEFIELD'
    DISSOLVEFIELD = 'DISSOLVEFIELD'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return DateDissolve()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'datedissolve'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Date Dissolve')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Example scripts')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'examplescripts'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Example algorithm short description")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.STARTDATEFIELD,
                self.tr('Start date field'),
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.DateTime
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.ENDDATEFIELD,
                self.tr('End date field'),
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.DateTime,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.DISSOLVEFIELD,
                self.tr('Dissolve field'),
                parentLayerParameterName=self.INPUT,
                allowMultiple=True
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        startDateField = self.parameterAsString(
            parameters,
            self.STARTDATEFIELD,
            context
        )
        endDateField = self.parameterAsString(
            parameters,
            self.ENDDATEFIELD,
            context
        )

        fields = source.fields()
        if not endDateField: fields.append(QgsField('ENDDATE', QVariant.DateTime, 'DateTime'))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            source.wkbType(),
            source.sourceCrs()
        )
        
        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        dissolveField = self.parameterAsFields(
            parameters,
            self.DISSOLVEFIELD,
            context
        )

        dissolveValues = set([tuple([feature[field] for field in dissolveField]) for feature in source.getFeatures()])
        feedback.pushInfo('dissolveValues is {}'.format(dissolveValues))

        for dissolveValueSet in dissolveValues:
            dissolveExpression = ' and '.join(['%s = %s'%(QgsExpression.quotedColumnRef(field),QgsExpression.quotedValue(value)) for field, value in zip(dissolveField, dissolveValueSet)])
            feedback.pushInfo('dissolveExpression is {}'.format(dissolveExpression))
            dissolveFilter = source.materialize(QgsFeatureRequest().setFilterExpression(dissolveExpression))
            
            features = list(dissolveFilter.getFeatures())
            feedback.pushInfo('got {} features'.format(len(features)))
            dates = set([feature[startDateField] for feature in features])
            if endDateField:
                dates.update([feature[endDateField] for feature in features])
            dates = list([date for date in dates if isinstance(date, QDateTime)])
            dates.sort()
            feedback.pushInfo('dates is {}'.format(dates))
            
            for i, startDate in enumerate(dates):
                # Stop the algorithm if cancel button has been clicked
                if feedback.isCanceled():
                    break
                
                endDate = dates[i+1] if i+1 < len(dates) else None
                
                dateExpression = '%s <= %s' % \
                    (QgsExpression.quotedColumnRef(startDateField),
                     QgsExpression.quotedValue(startDate))
                if endDateField:
                    if endDate:
                        dateExpression += ' and (%s >= %s or %s is null)' % \
                            (QgsExpression.quotedColumnRef(endDateField),
                             QgsExpression.quotedValue(endDate),
                             QgsExpression.quotedColumnRef(endDateField))
                    else:
                        dateExpression += ' and %s is null' % \
                            (QgsExpression.quotedColumnRef(endDateField))
                feedback.pushInfo('dateExpression is {}'.format(dateExpression))
                #req = QgsFeatureRequest().setFilterExpression(dateExpression)
                req = QgsFeatureRequest().setFilterExpression(dissolveExpression+' and '+dateExpression)
                feedback.pushInfo('req is {}'.format(req))
                #vl = dissolveFilter.materialize(req)
                vl = source.materialize(req)
                feedback.pushInfo('vl is {}'.format(vl))
                feedback.pushInfo('vl has {}'.format(list(vl.getFeatures())))
                if not vl.hasFeatures(): continue

                dissolved_layer = processing.run("native:dissolve", {
                    'INPUT': vl,
                    'OUTPUT': 'memory:'
                }, context=context)['OUTPUT']
                
                for f in dissolved_layer.getFeatures():
                    f[startDateField] = startDate
                    if endDateField: f[endDateField] = endDate
                    else:
                        f.setFields(fields)
                        f['ENDDATE'] = endDate
                    sink.addFeature(f)

                # Update the progress bar
                #feedback.setProgress(int(i * total))

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
