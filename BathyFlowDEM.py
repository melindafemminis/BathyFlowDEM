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

from qgis.core import Qgis, QgsProject, QgsVectorDataProvider, QgsField
from qgis.utils import iface
from qgis.core.additions.edit import edit
from qgis.gui import QgsMessageBar
import processing

from osgeo import gdal, osr
from osgeo.gdalconst import *

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .BathyFlowDEM_dialog import BathyFlowDEMDialog

import os.path
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel

from .interpolation import eidw
from .validation import differences, rmse
from .coordinates import get_s_and_flow_direction, shortest_dist, retrieve_n_coordinate
from .layers_helpers import create_sample_points, layer_to_raster_and_nodata






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
    



    ########################################################################
    ## To install and uninstall plugin
    ########################################################################
    
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI.
        Called only once on install (or on reload if dev)
        """

        icon_path = ':/plugins/BathyFlowDEM/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create DEM'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        self.dlg.boxRMSEresults.hide()

        # Connect dialog signals and slots for user interaction with GUI
        self.dlg.cbInputPointLayer.layerChanged.connect(self.oncbInputPointLayerWidget_layerChanged)
        self.dlg.cbTempLayer.stateChanged.connect(self.oncbTempLayer_stateChanged)
        self.dlg.buttonOK.clicked.connect(self.onStart)
        self.dlg.buttonCancel.clicked.connect(self.onCancel)

        # Populate attribute field 
        self.oncbInputPointLayerWidget_layerChanged()

        # Create message bar for user communication // ui must be in vertical layout
        self.plugin_message_bar = QgsMessageBar()
        self.dlg.verticalLayout.insertWidget(0, self.plugin_message_bar)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI when uninstalling plugin"""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&BathyFlowDEM'),
                action)
            self.iface.removeToolBarIcon(action)




    ########################################################################
    ## Tests and checks
    ########################################################################

    def allFieldsHaveLayer(self):

        points = self.dlg.cbInputPointLayer.currentLayer()
        centerline = self.dlg.cbInputVectorCenterline.currentLayer()
        polygon = self.dlg.cbInputROI.currentLayer()

        if points == None or centerline == None or polygon == None:
           return False
        else: 
            return True


    def outputPathExists(self):

        path = self.dlg.saveDirWidget.filePath() 

        if not path: 
            return False
        else:
            return True



    ########################################################################
    ## Methods linkes to Qt Widgets
    ########################################################################
    
    def clearMessageBar(self):
        self.plugin_message_bar.clearWidgets()


    def showWarningMessage(self, message):
        self.plugin_message_bar.pushMessage(message, level=Qgis.Warning)


    def onStart(self):
        """
        Called when the OK button is clicked. 
        Tests validity of the data and run the main function run()
        """

        self.dlg.boxRMSEresults.hide()

        # Checks validity of user's inputs
        if self.allFieldsHaveLayer() == False:
           self.plugin_message_bar.pushMessage("Warning", "All input fields must have a layer selected.", level=Qgis.Warning)
        elif self.dlg.cbTempLayer.isChecked() == False and self.outputPathExists() == False:
            self.plugin_message_bar.pushMessage("Warning", "Set output path or check 'Save to  temporary layer'.", level=Qgis.Warning)
        else: 
            self.run()


    def onCancel(self):
        """
        Called when the Cancel button is clicked.
        Closes the plugin window.
        """
        self.clearMessageBar()
        self.dlg.close()


    def oncbInputPointLayerWidget_layerChanged(self):
        """Slot method called when the seleted layer in cbInputPointLayer is changed"""

        current_point_layer = self.dlg.cbInputPointLayer.currentLayer()
        self.dlg.cbAttField.setLayer(current_point_layer)
        self.dlg.cbAttField.setFilters(QgsFieldProxyModel.Numeric)


    def oncbTempLayer_stateChanged(self):
        """
        Slot method called when cbTempLayer checkbox's state changes. (click)
        """

        cbTempLayer = self.dlg.cbTempLayer

        if cbTempLayer.isChecked() == True: 
            self.dlg.saveDirWidget.setEnabled(False)
            self.dlg.cbOpenOutputFile.setEnabled(False)
        else: 
            self.dlg.saveDirWidget.setEnabled(True)
            self.dlg.cbOpenOutputFile.setEnabled(True)
            



    def run(self):
        """Main method"""

        ########################################################################
        ## Set the dialog window, restrictions and updates
        ########################################################################
        # Restrict the type of layer that can be selected in the combo boxes
        self.dlg.cbInputROI.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.cbInputPointLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.dlg.cbInputVectorCenterline.setFilters(QgsMapLayerProxyModel.LineLayer)

        # Show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # Populate attribute field with selected point layer - and update if changed
        self.oncbInputPointLayerWidget_layerChanged()

        # Enables/disablesQgsFileWidget
        self.oncbTempLayer_stateChanged()


        if result:

            ########################################################################
            ## Get selected user's values INPUTS and OUTPUT choice/destination
            ########################################################################
            # Get user input layers an
            point_layer = self.dlg.cbInputPointLayer.currentLayer()
            centerline_layer = self.dlg.cbInputVectorCenterline.currentLayer()
            boundary_layer = self.dlg.cbInputROI.currentLayer()

            # Get name of field to interpolate
            field_to_interpolate = str(self.dlg.cbAttField.currentText())

            # Other parameters
            cell_size = self.dlg.sbCellSize.value()
            anisotropy_value = self.dlg.sbAnisotropyValue.value()
            max_distance = self.dlg.sbMaxDist.value()

            # Get user choice for saving final layer
            if self.dlg.cbTempLayer.isChecked():      
                saving_option = 'Save to temporary layer'
            else:
                if self.dlg.cbOpenOutputFile.isChecked():
                    saving_option = 'Save to folder and load'
                else: 
                    saving_option = 'Save to folder only'


            ########################################################################
            ## Create new points layer with S and N coordinates and flow direction
            ########################################################################       
            # Clone input shp point layer: comes with all attributes
            point_layer.selectAll()
            point_layer_SN = processing.run("native:saveselectedfeatures", {'INPUT': point_layer,
                                                                               'OUTPUT': 'TEMPORARY_OUTPUT'})['OUTPUT']
            point_layer.removeSelection()
            point_layer_SN.setName('Points SN')
            
            # To enable check of a particular capability 
            pl_caps = point_layer_SN.dataProvider().capabilities()

            # Create list of new fields
            pl_new_fields = [
                QgsField("S", QVariant.Double),
                QgsField("N", QVariant.Double),
                QgsField("FlowDir", QVariant.Double),
            ]

            # Add fields to layer and update layer
            if pl_caps & QgsVectorDataProvider.AddAttributes:
                 point_layer_SN.dataProvider().addAttributes(pl_new_fields)
            point_layer_SN.updateFields()

            # Get field's id from name for later
            pointSN_fields = point_layer_SN.fields()
            s_index = pointSN_fields.indexFromName("S")
            n_index = pointSN_fields.indexFromName("N")
            flowdir_index = pointSN_fields.indexFromName("FlowDir")

            # Calculate S, N and flow direction
            shortest_dist_point_centerline_layer = shortest_dist(point_layer_SN, centerline_layer)
            infos_dict = get_s_and_flow_direction(point_layer_SN, centerline_layer)

            # Populate the new layer with S, N and FlowDir values
            with edit(point_layer_SN):

                for f in point_layer_SN.getFeatures():

                    n_coordinate = retrieve_n_coordinate(f, shortest_dist_point_centerline_layer, infos_dict)
                    flow_direction =  infos_dict[f.id()]['flowdir']
                    s_coordinate = infos_dict[f.id()]['distance_along_line']

                    # Add values to the layer
                    point_layer_SN.changeAttributeValue(f.id(), s_index, s_coordinate)
                    point_layer_SN.changeAttributeValue(f.id(), n_index, n_coordinate)   
                    point_layer_SN.changeAttributeValue(f.id(), flowdir_index, flow_direction)      

            # Add new layer to project
            QgsProject.instance().addMapLayer(point_layer_SN)


            ########################################################################
            ## Prepare new layers for interpolation
            ########################################################################   
            raster_ROI_extent, sampled_points = create_sample_points(point_layer, cell_size, boundary_layer)

            # Prepare fields for the sampled_points layer
            sp_caps = sampled_points.dataProvider().capabilities()

            # Get field's id from name for later
            sp_all_fields = sampled_points.fields()
            s_index = sp_all_fields.indexFromName("S")
            n_index = sp_all_fields.indexFromName("N")

            # Get S and N coordinates information
            shortest_dist_point_centerline_layer_sampled = shortest_dist(sampled_points, centerline_layer)
            infos_dict_sampled = get_s_and_flow_direction(sampled_points, centerline_layer)

            # Populate the new layer with S, N and FlowDir values
            with edit(sampled_points):
                for f in sampled_points.getFeatures():
                    n_coordinate = retrieve_n_coordinate(f, shortest_dist_point_centerline_layer_sampled, infos_dict_sampled)
                    flow_direction =  infos_dict_sampled[f.id()]['flowdir']
                    s_coordinate = infos_dict_sampled[f.id()]['distance_along_line']

                    # Add values to the layer
                    sampled_points.changeAttributeValue(f.id(), s_index, s_coordinate) 
                    sampled_points.changeAttributeValue(f.id(), n_index, n_coordinate)

 
            ########################################################################
            ## interpolate value for each point
            ########################################################################  
            # second loop necessary so that SN info are saved
            with edit(sampled_points):
                for f in sampled_points.getFeatures():

                    # Get interpolated value for the point
                    interpolated_value = eidw(target_s=f['S'], 
                                                    target_n=f['N'], 
                                                    value_field=field_to_interpolate, 
                                                    point_layer=point_layer_SN, 
                                                    anisotropy_ratio=anisotropy_value, 
                                                    max_distance=max_distance)
                    sampled_points.changeAttributeValue(f.id(), 2, interpolated_value)
            

            ########################################################################
            ## Add interpolated values to raster cells and save
            ########################################################################   
            # Create full path to save final raster
            folder_path = self.dlg.saveDirWidget.filePath()
            dataname = 'Interpolated raster'
            full_path = os.path.join(folder_path, dataname + '.tif' )
            
            # Parameters is temporary layer 
            params = {
                'INPUT': sampled_points,
                'FIELD': 'Interpolated',
                'DATA_TYPE': 5,
                'BURN': 0,
                'USE_Z':False,
                'UNITS':1,
                'WIDTH': cell_size,
                'HEIGHT': cell_size,
                'EXTENT': raster_ROI_extent.extent(),
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }

            # Parameters of save to folder
            params_save = {
                'INPUT': sampled_points,
                'FIELD': 'Interpolated',
                'DATA_TYPE': 5,
                'BURN': 0,
                'USE_Z':False,
                'UNITS':1,
                'WIDTH': cell_size,
                'HEIGHT': cell_size,
                'EXTENT': raster_ROI_extent.extent(),
                'OUTPUT': full_path
            }

            if saving_option == 'Save to temporary layer':    
                rasterize_raster = processing.run("gdal:rasterize", params)['OUTPUT']
                final_raster = layer_to_raster_and_nodata(rasterize_raster, 0) # QgsRasterLayer to output + nodata
                QgsProject.instance().addMapLayer(final_raster)

                self.plugin_message_bar.pushMessage("Success", "File loaded to project.", level=Qgis.Success)

            else:
                if saving_option == 'Save to folder and load':
                    rasterize_raster = processing.run("gdal:rasterize", params_save)['OUTPUT']
                    final_raster = layer_to_raster_and_nodata(rasterize_raster, 0) # QgsRasterLayer to output + nodata
                    QgsProject.instance().addMapLayer(final_raster)

                    self.plugin_message_bar.pushMessage("Success", f"File loaded and saved to {full_path}.", level=Qgis.Success)

                elif saving_option == 'Save to folder only':
                    rasterize_raster = processing.run("gdal:rasterize", params_save)['OUTPUT']
                    final_raster = layer_to_raster_and_nodata(rasterize_raster, 0) # QgsRasterLayer to output + nodata

                    self.plugin_message_bar.pushMessage("Success", f"File loaded and saved to {full_path}.", level=Qgis.Success)


            ########################################################################
            ## For each input point in the ROI, calculate the difference between actual point and raster cell + total rmse
            ########################################################################   
            if self.dlg.cbModelEvaluation.isChecked():

                actual_values, predicted_values, differences_layer = differences(point_layer=point_layer, 
                                                                                 boundary_layer=boundary_layer,
                                                                                 raster=final_raster,
                                                                                 field=field_to_interpolate)
                QgsProject.instance().addMapLayer(differences_layer)

                rmse_value = rmse(actual_values=actual_values, 
                            predicted_values=predicted_values)
                
                self.dlg.boxRMSEresults.show()
                self.dlg.labelRMSE.setText(f"Final RMSE: {rmse_value}")
            
