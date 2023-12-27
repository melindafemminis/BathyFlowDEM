# Specifications of BathyFlowDEM

## Introduction

### Objectives and goals

Create a QGIS plugin that uses anisotropic interpolation methods and flow-oriented coordinate system to output a DEM from cross-sections data of a river or reservoir surveyed with a single-beam echosounder. 

### Main steps

- First minimal version: January 7th 2024
- Final working version: April 30th 2024

## Development

### Dependencies

- QGIS 3.XX

This plugin will be available for download directly from the QGIS interface. 

### Minimum features

With a given input data in a specific tbd format, convert to to flow oriented coordinate system and use anisotropic interpolation method to create a surface. The output will be a DEM raster file with boundary and a specific CRS. 
No user input in this first version.

### Full version features

The same as the above, plus:

- conversion of data input from data CRS to projected UTM
- add user defined parameters

### Extra features

The same as the above, plus the possibilty to choose between different interpolation algorithms.

## Steps

### First version

- Graphical interface is complete for the minimum features
- Minimum features are implemented and have been tested

### Final verison

- Full graphical interface
- All full version features have been implemented and tested
- The plugin documentation and user manual is complete

ß

