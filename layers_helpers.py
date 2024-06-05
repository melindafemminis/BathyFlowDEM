import processing
from qgis.core import QgsRasterLayer


def create_sample_points(survey_points_layer, pixel_size, ROI):
        ''' 
        Creates new raster layer and samples 1 point per pixel in the center.

        Args: 
            survey_points_layer (QgsVectorLayer): containing original survey points. used to retrieve CRS
            ROI (QgsVectorLayer): Region Of Interest, boundary layer used to retrieve extent
            pixel_size (Int): user defined pixel size

        Returns:
            QgsRasterLayer with the new raster
            QgsVectorLayer with the sampled points
        '''

        # Create raster layer
        create_raster_params = {'EXTENT': ROI.extent(),
                                'TARGET_CRS': survey_points_layer.crs(),
                                'PIXEL_SIZE': pixel_size,
                                'OUTPUT_TYPE': 5,
                                'OUTPUT': 'TEMPORARY_OUTPUT'}
        
        created_raster = processing.run("native:createconstantrasterlayer", create_raster_params)
        new_raster = QgsRasterLayer(created_raster['OUTPUT'], 'Grid_empty')

        pixelpoint_params = {'INPUT_RASTER': new_raster,
                             'RASTER_BAND': 1,
                             'FIELD_NAME': 'VALUE',
                             'OUTPUT': 'TEMPORARY_OUTPUT'}
        
        sampled_points = processing.run("native:pixelstopoints", pixelpoint_params)['OUTPUT']

        return new_raster, sampled_points


def layer_to_raster_and_nodata(raster, nodata):
    """
    Converts the output of a raster algorithm to a layer and adds nodata value to its band 1

    Args:
        raster (QgsRasterLayer)
        nodata (int/float): to add to the nodata values

    Returns:
        raster (QgsRasterLayer); named Interpolated raster with nodata set
    """

    final_raster = QgsRasterLayer(raster, 'Interpolated raster')
    provider = final_raster.dataProvider()
    provider.setNoDataValue(1, nodata)
    final_raster.triggerRepaint()
    
    return final_raster