import math
import processing

from qgis.core import QgsAggregateCalculator

def differences(point_layer, extent, raster, field):
        
    # Select only points used for interpolation
    clip_params = {
        'INPUT': point_layer, 
        'OVERLAY': extent,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }
    used_points = processing.run("native:clip", clip_params)['OUTPUT']

    sample_params = {
        'INPUT': used_points,
        'RASTERCOPY': raster,
        'COLUMN_PREFIX': 'SAMPLE_',
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }

    used_points_with_sampled_raster = processing.run("native:rastersampling", sample_params)['OUTPUT']
    used_points_with_sampled_raster.setName('Data validation - differences')

    actual_values = used_points_with_sampled_raster.aggregate(QgsAggregateCalculator.ArrayAggregate, field)[0]
    predicted_values = used_points_with_sampled_raster.aggregate(QgsAggregateCalculator.ArrayAggregate, 'SAMPLE_1')[0]

    return actual_values, predicted_values, used_points_with_sampled_raster

def rmse(actual_values, predicted_values):
        
        differences = []
        for pred, act in zip(predicted_values, actual_values):
            try:
                diff = pred - act
                differences.append(diff)
            except TypeError:
                print(f"TypeError: Unsupported operand types for -: '{type(pred)}' and '{type(act)}'")

        squared_differences = [diff ** 2 for diff in differences]

        mean_squared_difference = sum(squared_differences) / len(squared_differences)
        print(f'Mean squared difference: {mean_squared_difference}')
        rmse = math.sqrt(mean_squared_difference)
        
        return rmse