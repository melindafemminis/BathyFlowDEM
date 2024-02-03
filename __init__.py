# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BathyFlowDEM
                                 A QGIS plugin
 Interpolation plugin for bathymetric data
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2023-12-28
        copyright            : (C) 2023 by Melinda Femminis
        email                : Contact
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load BathyFlowDEM class from file BathyFlowDEM.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .BathyFlowDEM import BathyFlowDEM
    return BathyFlowDEM(iface)
