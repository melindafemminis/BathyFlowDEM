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

from qgis.core import Qgis, QgsProject, QgsVectorDataProvider, QgsField, QgsGeometry, QgsPointXY, QgsFeatureRequest, QgsJsonUtils
from qgis.utils import iface
from qgis.core.additions.edit import edit
import processing

from osgeo import gdal
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
        self.dlg.cbInputPoints.layerChanged.connect(self.onCbInputPointsWidget_layerChanged)

        # Populate attribute field with selected point layer
        self.onCbInputPointsWidget_layerChanged()




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




    def onCbInputPointsWidget_layerChanged(self):
        """Slot method called when the seleted layer in cbInputPoints is changed"""

        current_point_layer = self.dlg.cbInputPoints.currentLayer()
        self.dlg.cbAttributeFields.setLayer(current_point_layer)
        self.dlg.cbAttributeFields.setFilters(QgsFieldProxyModel.Numeric)
        print("Point layer changed method.")









    ########################################################################
    ##
    ## Creates a memory layer that 
    ##
    ########################################################################



    def shortest_distance(self, centerline, points):
        """Creates lines that are the shortest between each bathy points and the centerline"""
        print("Inside the shortest_distance().")

        # Parameters dictionnary for the shortest distance algorithm
        short_dist_params = {
            'SOURCE': points,
            'DESTINATION': centerline,
            'METHOD': 0,
            'NEIGHBORS': 1,
            'END_OFFSET': 0,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }

        # Run the algorithm
        short_dist_layer = processing.run("native:shortestline", short_dist_params)['OUTPUT']

        # Add to map for vizualisation
        # QgsProject.instance().addMapLayer(short_dist_layer) 

        return short_dist_layer













    ########################################################################
    ##
    ## Find the distance along a line
    ##
    ########################################################################
    
    

    def calculate_distances_along_line(self, points, centerline):
        """ Function that returns a dictionnary with, for each point, the side of the line it is located in "side" and the 
        distance along the center line in "distance". """

        # Initialize a dictionary to store distances along the line for each point
        sn_coordinates_dict = {}

        line_feature = next(centerline.getFeatures())
        line_geom = line_feature.geometry()

        # Iterate over each feature in the point layer
        for point_feature in points.getFeatures():
            point_geom = point_feature.geometry()
            # closestSegmentWithContext() returns a tuple with [point, nearest point on segment, ]
            nearest_segment = line_geom.closestSegmentWithContext(point_geom.asPoint())

            if nearest_segment:
                side = nearest_segment[3]

                distance_along_line = line_geom.lineLocatePoint(point_geom)

                sn_coordinates_dict[point_feature.id()] = {
                    'side': side,
                    'distance_along_line': distance_along_line
                }

        return sn_coordinates_dict








    def run(self):
        """Run method that performs all the real work"""





        ########################################################################
        ##
        ## Set the dialog window, restrictions and updates
        ##
        ########################################################################

        # Restrict the type of layer that can be selected in the combo boxes
        self.dlg.cbInputBoundary.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.cbInputPoints.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.dlg.cbInputCenterline.setFilters(QgsMapLayerProxyModel.LineLayer)

        # PLaceholders for output layer name
        self.dlg.leOutputName.setPlaceholderText("bathyflowDEM_output")

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # Populate attribute field with selected point layer - and update is changed
        self.onCbInputPointsWidget_layerChanged()
        
    





        # See if OK was pressed
        if result:



            ########################################################################
            ##
            ## Get selected user's values INPUTS and OUTPUT choice/destination
            ##
            ########################################################################
            
            # Get user input layers
            point_layer = self.dlg.cbInputPoints.currentLayer()
            centerline_layer = self.dlg.cbInputCenterline.currentLayer()
            boundary_layer = self.dlg.cbInputBoundary.currentLayer()

            # Other parameters
            cell_size = self.dlg.sbCellSize.value()
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
            ## Create new points layer with X, Y, S and N coordinates
            ##
            ########################################################################       


            # Clone input shp point layer: comes with all attributes: id, X and Y
            point_layer_xy_sn = point_layer.clone()
            point_layer_xy_sn.setName('points_xy_and_sn')
            
            # To enable check of a particular capability 
            pl_caps = point_layer_xy_sn.dataProvider().capabilities()

            # Create list of new fields
            pl_new_fields = [
                QgsField("S", QVariant.Double),
                QgsField("N", QVariant.Double),
            ]

            # Add fields to layer and update layer
            if pl_caps & QgsVectorDataProvider.AddAttributes:
                 point_layer_xy_sn.dataProvider().addAttributes(pl_new_fields)
            point_layer_xy_sn.updateFields()



            # Get the shortest distance from each point to the centerline $
            short_dist_params = {
            'SOURCE': point_layer,
            'DESTINATION': centerline_layer,
            'METHOD': 0,
            'NEIGHBORS': 1,
            'END_OFFSET': 0,
            'OUTPUT': 'TEMPORARY_OUTPUT'
            }
             # Run the algorithm
            shortest_dist_point_centerline_layer = processing.run("native:shortestline", short_dist_params)['OUTPUT']
            sn_infos_dictionnary = self.calculate_distances_along_line(centerline=centerline_layer, points=point_layer)




            # For each point, populate fields
            with edit(point_layer_xy_sn):

                for f in point_layer_xy_sn.getFeatures():

                    # Retrieve n, calculated by the shortest_distance algorithm
                    # setFilterFid() needs row number, not id so add 1
                    row = f['id'] + 1
                    iterator = shortest_dist_point_centerline_layer.getFeatures(QgsFeatureRequest().setFilterFid(row))
                    feature = next(iterator)
                    n = feature['distance']
                    
                    # Change the sign to negative according to which side of the centerline the point it located
                    if sn_infos_dictionnary[f.id()]['side'] == -1:
                        n *= -1

                    # Add s and n coordinates to attribute
                    point_layer_xy_sn.changeAttributeValue(f.id(), 3, sn_infos_dictionnary[f.id()]['distance_along_line'])
                    point_layer_xy_sn.changeAttributeValue(f.id(), 4, n)            



            # Add new layer to project
            QgsProject.instance().addMapLayer(point_layer_xy_sn)







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
      
            


