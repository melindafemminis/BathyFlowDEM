# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BathyFlowDEM
                                 A QGIS plugin
 Interpolation plugin for bathymetric data
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-12-28
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Melinda Femminis
        email                : Contact
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

import math

from qgis.core import Qgis, QgsProject, QgsVectorDataProvider, QgsField, QgsGeometry, QgsPointXY, QgsFeatureRequest, QgsRasterLayer, QgsRasterFileWriter
from qgis.utils import iface
from qgis.core.additions.edit import edit
import processing
from qgis.analysis import QgsIDWInterpolator

from osgeo import gdal, osr
from osgeo.gdalconst import *

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .BathyFlowDEM_dialog import BathyFlowDEMDialog

import os.path
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel






class BathyFlowDEM:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface                                                                                                                          
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BathyFlowDEM_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&BathyFlowDEM')

        # Create instance of dialog class
        self.dlg = BathyFlowDEMDialog()

        


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('BathyFlowDEM', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action
    




    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/BathyFlowDEM/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create DEM'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Connect dialog signals and slots
        self.dlg.cbInputPointLayer.layerChanged.connect(self.oncbInputPointLayerWidget_layerChanged)

        # Populate attribute field with selected point layer
        self.oncbInputPointLayerWidget_layerChanged()




    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&BathyFlowDEM'),
                action)
            self.iface.removeToolBarIcon(action)



    # Errors and exceptions functions
    def check_data_inputs(self, points, centerline, polygon):
        if points == None or centerline == None or polygon == None:
            self.iface.messageBar().pushMessage("Error", "All input fields must have a layer selected.", level=Qgis.Critical)
            pass
        elif str(points.fields().names()) != [str(['x', 'y', 'z']), str(['X', 'Y', 'Z'])]:
            self.iface.messageBar().pushMessage("Error", "Point layer's fields' names must be X,Y,Z. Modify and try again.", level=Qgis.Critical)
            pass
        else: 
            print(points.fields.names())
            return True   



    def oncbInputPointLayerWidget_layerChanged(self):
        """Slot method called when the seleted layer in cbInputPointLayer is changed"""

        current_point_layer = self.dlg.cbInputPointLayer.currentLayer()
        self.dlg.cbAttFields.setLayer(current_point_layer)
        self.dlg.cbAttFields.setFilters(QgsFieldProxyModel.Numeric)
        print("Point layer changed method.")


















    ########################################################################
    ##
    ## Find the distance along a line
    ##
    ########################################################################
    
    def get_s_and_flow_direction(self, survey_points_layer, centerline):
        """
        Calculates for each point the distance along a line , the side of the line it's on and segment direction.

        Args:
            centerline_layer (QgsVectorLayer): Input layer with a single line of flow direction
            survey_points_layer (QgsVectorLayer): Input layer with points

        Returns:
            dictionnary: Key is point ID with side, distance along line and flowdir values.
        """

        # Initialize a dictionary to store the values
        results_dir = {}

        line_feature = next(centerline.getFeatures())
        line_geom = line_feature.geometry()

        # Iterate over each feature in the point layer
        for point_feature in survey_points_layer.getFeatures():
            point_geom = point_feature.geometry()
            minDist, closest_pt, afterVertex, leftOf = line_geom.closestSegmentWithContext(point_geom.asPoint())

            # To know on which side of the center line the point lies
            side = leftOf

            # To know the distance along the center line for each point
            distance_along_line = line_geom.lineLocatePoint(point_geom)

            # To know flow direction, get vertex before and after point
            before_vertex_index = afterVertex - 1

            start_point = line_geom.vertexAt(before_vertex_index)
            end_point = line_geom.vertexAt(afterVertex)

            # Calculate flow direction as an angle
            if start_point and end_point:

                dx = end_point.x() - start_point.x()
                dy = end_point.y() - start_point.y()
                # Calculates the angle in radians of the segment relative to the horizontal axis, 
                # taking into account the correct quadrant.
                angle_rad = math.atan2(dy, dx)
                angle_deg = math.degrees(angle_rad)
            else:
                angle_deg = None
        

            results_dir[point_feature.id()] = {'side': side, 
                                                'distance_along_line': distance_along_line,
                                                'flowdir': angle_deg}

        return results_dir






    ########################################################################
    ##
    ## Create a new raster layer to user's specifications
    ##
    ########################################################################

    def create_raster_and_sample_points(self, survey_points_layer, pixel_size, ROI):
        ''' 
        Creates new raster layer and sample 1 point per pixel

        Args: 
            survey_points_layer (QgsVectorLayer): containing original survey points. used to retrieve CRS
            ROI (QgsVectorLayer): Region Of Interest, boundary layer used to retrieve extent
            pixel_size (Int): user defined pixel size

        Returns:
            QgsRasterLayer with specified extent, crs and pixel_size
            QgsVectorLayer with the sampled points
        '''
        print("In the create_raster_and_sample_points() function.")


        # Create raster alyer
        create_raster_parars = {'EXTENT': ROI.extent(),
                                'TARGET_CRS': survey_points_layer.crs(),
                                'PIXEL_SIZE': pixel_size,
                                'OUTPUT_TYPE': 5,
                                'OUTPUT': 'TEMPORARY_OUTPUT'}
        
        created_raster = processing.run("native:createconstantrasterlayer", create_raster_parars)
        new_raster = QgsRasterLayer(created_raster['OUTPUT'], 'Grid_empty')


        # Sample one point per pixel
        pixelpoint_params = {'INPUT_RASTER': new_raster,
                             'RASTER_BAND': 1,
                             'FIELD_NAME': 'VALUE',
                             'OUTPUT': 'TEMPORARY_OUTPUT'}
        
        sampled_points = processing.run("native:pixelstopoints", pixelpoint_params)['OUTPUT']

        QgsProject.instance().addMapLayer(new_raster)

        return new_raster, sampled_points








    ########################################################################
    ##
    ## Interpolation
    ##
    ########################################################################
        
    def eidw(self, target_s, target_n, value_field, point_layer, anisotropy_ratio, max_distance):
        """
        Perform IDW interpolation using anisotropy along the already aligned S and N coordinates.

        Args:
            point_layer (QgsVectorLayer): Input layer with point features containing S, N, and Z.
            value_field (str): Name of the field with values to interpolate.
            target_s (float): Target point's S coordinate.
            target_n (float): Target point's N coordinate.
            anisotropy_ratio (float): Factor by which distances across the flow (N direction) are scaled.

        Returns:
            float: Interpolated value at the target location or -9999 if no data
        """
        sum_weighted_values = 0
        sum_weights = 0
        distances = []
        
        for feature in point_layer.getFeatures():
            s = feature['S']
            n = feature['N']
            value = feature[value_field]
            
            # Calculate distances in the S and N directions
            ds = s - target_s
            dn = (n - target_n) * anisotropy_ratio

            # Calculate the anisotropic distance by modifying it on the N axis
            distance = (ds**2 + dn**2) ** 0.5

            if distance <= max_distance:
                distances.append((distance, value))
            
            if distance < 0.0001:  # If point is right on it/super close
                return value
                        
        if not distances:
            return -9999
        else:
            for distance, value, in distances:
                weight = 1 / distance
                sum_weights += weight
                sum_weighted_values += weight * value
            
            if sum_weights == 0:
                return None 
            
            return sum_weighted_values / sum_weights
              
        











    def run(self):
        """Run method that performs all the real work"""





        ########################################################################
        ##
        ## Set the dialog window, restrictions and updates
        ##
        ########################################################################

        # Restrict the type of layer that can be selected in the combo boxes
        self.dlg.cbInputROI.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.cbInputPointLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.dlg.cbInputVectorCenterline.setFilters(QgsMapLayerProxyModel.LineLayer)

        # PLaceholders for output layer name
        self.dlg.leOutputName.setPlaceholderText("bathyflowDEM_output")

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # Populate attribute field with selected point layer - and update is changed
        self.oncbInputPointLayerWidget_layerChanged()
        
    










        # See if OK was pressed
        if result:



            ########################################################################
            ##
            ## Get selected user's values INPUTS and OUTPUT choice/destination
            ##
            ########################################################################
            
            # Get user input layers
            point_layer = self.dlg.cbInputPointLayer.currentLayer()
            centerline_layer = self.dlg.cbInputVectorCenterline.currentLayer()
            boundary_layer = self.dlg.cbInputROI.currentLayer()

            # Other parameters
            cell_size = self.dlg.sbCellSize.value()
            anisotropy_value = self.dlg.sbAnisotropyValue.value()
            show_output_checked = self.dlg.cbOpenOutputFile.isChecked()

            # Get user output path 
            user_output_dir_path = self.dlg.saveDirWidget.filePath() # might be empty
            print("User dir " + str(user_output_dir_path))
            user_output_layer_name = self.dlg.leOutputName.displayText() # might be empty
            print("User layer name " + str(user_output_layer_name))

            # Define user output path. If no directory selected, layer name is ditched. Otherwise build full path.
            if not user_output_dir_path:
                pass
            else:
                if not user_output_layer_name:
                    output_path = user_output_dir_path + "\\bathyflowdem_output.shp"
                else:
                    output_path = user_output_dir_path + "\\" + user_output_layer_name + ".shp"

        







            
            ########################################################################
            ##
            ## Create new points layer with X, Y, S and N coordinates and flow direction
            ##
            ########################################################################       

            # Clone input shp point layer: comes with all attributes: id, X and Y
            point_layer.selectAll()
            point_layer_xy_sn = processing.run("native:saveselectedfeatures", {'INPUT': point_layer,
                                                                               'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            point_layer.removeSelection()
            point_layer_xy_sn.setName('points_xy_and_sn')
            print(point_layer_xy_sn)
            
            # To enable check of a particular capability 
            pl_caps = point_layer_xy_sn.dataProvider().capabilities()

            # Create list of new fields
            pl_new_fields = [
                QgsField("S", QVariant.Double),
                QgsField("N", QVariant.Double),
                QgsField("FlowDir", QVariant.Double),
            ]

            # Add fields to layer and update layer
            if pl_caps & QgsVectorDataProvider.AddAttributes:
                 point_layer_xy_sn.dataProvider().addAttributes(pl_new_fields)
            point_layer_xy_sn.updateFields()



            # Get N for each point, the distance to the centerline
            short_dist_params = {'SOURCE': point_layer_xy_sn,
                                'DESTINATION': centerline_layer,
                                'METHOD': 0,
                                'NEIGHBORS': 1,
                                'END_OFFSET': 0,
                                'OUTPUT': 'TEMPORARY_OUTPUT'
                                }
             # Run the algorithm
            shortest_dist_point_centerline_layer = processing.run("native:shortestline", short_dist_params)['OUTPUT']


            # Get S and flow direction for each point
            infos_dict = self.get_s_and_flow_direction(centerline=centerline_layer, survey_points_layer=point_layer_xy_sn)


            # Populate the new layer with S, N and FlowDir values
            with edit(point_layer_xy_sn):

                for f in point_layer_xy_sn.getFeatures():

                    # Retrieve n, calculated by the shortest_distance algorithm
                    iterator = shortest_dist_point_centerline_layer.getFeatures(QgsFeatureRequest().setFilterFid(f.id()))
                    feature = next(iterator)
                    n_coordinate = feature['distance']
                    
                    # Change the sign to negative according to which side of the centerline the point it located
                    if infos_dict[f.id()]['side'] == -1:
                        n_coordinate *= -1

                    flow_direction =  infos_dict[f.id()]['flowdir']

                    s_coordinate = infos_dict[f.id()]['distance_along_line']

                    # Add values to the layer
                    point_layer_xy_sn.changeAttributeValue(f.id(), 4, s_coordinate)
                    point_layer_xy_sn.changeAttributeValue(f.id(), 5, n_coordinate)   
                    point_layer_xy_sn.changeAttributeValue(f.id(), 6, flow_direction)            

            # Add new layer to project
            QgsProject.instance().addMapLayer(point_layer_xy_sn)







            new_raster, sampled_points = self.create_raster_and_sample_points(point_layer, cell_size, boundary_layer)

            # To enable check of a particular capability 
            sp_caps = sampled_points.dataProvider().capabilities()

            # Delete VALUE field created by pixel to layer native algorithm
            if sp_caps & QgsVectorDataProvider.DeleteAttributes:
                sampled_points.dataProvider().deleteAttributes([0])

            # Create list of new fields
            sp_new_fields = [
                QgsField("S", QVariant.Double),
                QgsField("N", QVariant.Double),
                QgsField("Interpolated", QVariant.Double)
            ]

            # Add fields to layer and update layer
            if sp_caps & QgsVectorDataProvider.AddAttributes:
                 sampled_points.dataProvider().addAttributes(sp_new_fields)
            sampled_points.updateFields()

            # Get N for each point, the distance to the centerline
            short_dist_params = {'SOURCE': sampled_points,
                                'DESTINATION': centerline_layer,
                                'METHOD': 0,
                                'NEIGHBORS': 1,
                                'END_OFFSET': 0,
                                'OUTPUT': 'TEMPORARY_OUTPUT'
                                }
             # Run the algorithm
            shortest_dist_point_centerline_layer_sampled = processing.run("native:shortestline", short_dist_params)['OUTPUT']

            # Get S and flow direction for each point
            infos_dict_sampled = self.get_s_and_flow_direction(centerline=centerline_layer, survey_points_layer=sampled_points)

            # Populate the new layer with S, N and FlowDir values
            with edit(sampled_points):

                for f in sampled_points.getFeatures():

                    # Retrieve n, calculated by the shortest_distance algorithm
                    # setFilterFid() needs row number, not id, so add 1
                    iterator = shortest_dist_point_centerline_layer_sampled.getFeatures(QgsFeatureRequest().setFilterFid(f.id()))
                    feature = next(iterator)
                    n_coordinate = feature['distance']
                    
                    # Change the sign to negative according to which side of the centerline the point it located
                    if infos_dict_sampled[f.id()]['side'] == -1:
                        n_coordinate *= -1

                    s_coordinate = infos_dict_sampled[f.id()]['distance_along_line']

                    # Add values to the layer
                    sampled_points.changeAttributeValue(f.id(), 0, s_coordinate) 
                    sampled_points.changeAttributeValue(f.id(), 1, n_coordinate)

            with edit(sampled_points):

                for f in sampled_points.getFeatures():

                    # Get interpolated value for the point
                    Z = self.eidw(target_s = f['S'], 
                                target_n = f['N'], 
                                value_field = 'Z', 
                                point_layer=point_layer_xy_sn, 
                                anisotropy_ratio=5, 
                                max_distance=20)

                    sampled_points.changeAttributeValue(f.id(), 2, Z)

            QgsProject.instance().addMapLayer(sampled_points)


            
            # Rasterize over the existing raster using attributes from the vector layer
            params = {
                'INPUT': sampled_points,
                'FIELD': 'Interpolated',  # Replace 'attribute_name' with the actual field name from your vector layer
                'BURN': 0,  # This is optional and is used if you want a specific burn value; it's often left out when using FIELD
                'ADD': False,  # Set to True to add values to existing data instead of overwriting
                'INPUT_RASTER': new_raster,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }

            result = processing.run("gdal:rasterize_over", params)

            interpolated_raster = QgsRasterLayer(result['OUTPUT'], 'Interpolated raster')

            QgsProject.instance().addMapLayer(interpolated_raster)










            """Tests and errors"""
            # self.check_data_inputs(point_layer, centerline_layer, boundary_layer)


            if show_output_checked == True:

                # No output dir selected, no layer name but load layer checked
                if not user_output_dir_path and not user_output_layer_name: 
                    print("Load layer to map checked, no dir and not output name.")

                    """ new_layer = processing.runAndLoadResults("native:centroids", {'INPUT':boundary_layer,
                                                                                  'ALL_PARTS':False,
                                                                                  'OUTPUT':'TEMPORARY_OUTPUT', 
                                                                                  'NAME':'bathyflowDEM_output'})"""
                    
                # if there is a dir path, output path was defined earlier
                elif not user_output_dir_path:
                    print("Load layer to map checked, no dir path selected so only temp.")
                    """ new_layer = processing.runAndLoadResults("native:centroids", {'INPUT':boundary_layer,
                                                                                  'ALL_PARTS':False,
                                                                                  'OUTPUT': output_path}) """

                else:
                    print("Load layer to map checked, dir selected so load in project + export with output path.")
                    self.iface.messageBar().pushMessage("BathyFlowDEM", "Finished. New layer saved at " + output_path, level=Qgis.Success)

            else:

                # if no output dir selected
                if not user_output_dir_path: # wether user added filename or not
                    print("ERROR, there is no saving path and no load to project. Choose one method.")
                    self.iface.messageBar().pushMessage("BathyFlowDEM", "Choose output directory or to load temporary layer.", level=Qgis.Warning)


                else: # if there is a dir path, output path was defined earlier
                    print("Box to laod layer not checked, dir path selected.")
                    """ new_layer = processing.run("native:centroids", {'INPUT':boundary_layer,
                                                                    'ALL_PARTS':False,
                                                                    'OUTPUT': output_path}) """
                    self.iface.messageBar().pushMessage("BathyFlowDEM", "Finished. New layer saved at " + output_path, level=Qgis.Success)
      
            


