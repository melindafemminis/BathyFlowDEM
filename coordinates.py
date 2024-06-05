import math
import processing

from qgis.core import Qgis
from qgis.core.additions.edit import edit


def get_s_and_flow_direction(point_layer, centerline):
        """
        Calculates for each point the distance along a line , the side of the line it's on and segment direction.

        Args:
            centerline_layer (QgsVectorLayer): Input layer with a single line of flow direction
            survey_points_layer (QgsVectorLayer): Input layer with points

        Returns:
            dictionnary: Key is point ID with side, distance along line and flowdir values.
        """

        results_dir = {}

        # In case more than one line, will get the first one
        line_feature = next(centerline.getFeatures())
        line_geom = line_feature.geometry()

        # Iterate over each feature in the point layer
        for point_feature in point_layer.getFeatures():
            point_geom = point_feature.geometry()
            minDist, closest_pt, afterVertex, leftOf = line_geom.closestSegmentWithContext(point_geom.asPoint())

            side = leftOf
            distance_along_line = line_geom.lineLocatePoint(point_geom)

            # To know flow direction, get vertex before and after point
            before_vertex_index = afterVertex - 1
            start_point = line_geom.vertexAt(before_vertex_index)
            end_point = line_geom.vertexAt(afterVertex)

            # Calculate flow direction as an angle
            if start_point and end_point:

                dx = end_point.x() - start_point.x()
                dy = end_point.y() - start_point.y()
                # Calculates the angle in radians of the segment relative to the horizontal axis, taking into account the correct quadrant.
                angle_rad = math.atan2(dy, dx)
                angle_deg = math.degrees(angle_rad)
            else:
                angle_deg = None
        
            results_dir[point_feature.id()] = {'side': side, 
                                                'distance_along_line': distance_along_line,
                                                'flowdir': angle_deg}

        return results_dir


def shortest_dist(point_layer, centerline):

    short_dist_params = {'SOURCE': point_layer,
                        'DESTINATION': centerline,
                        'METHOD': 0,
                        'NEIGHBORS': 1,
                        'END_OFFSET': 0,
                        'DISTANCE': None,
                        'OUTPUT': 'TEMPORARY_OUTPUT'}
    result_layer = processing.run("native:shortestline", short_dist_params)['OUTPUT']
    
        
    # Add line length to distance field if not there already 
    if result_layer.isValid():
        with edit(result_layer):
            for feature in result_layer.getFeatures():
                if feature['distance'] is None:
                    feature['distance'] = feature.geometry().length()
                    result_layer.updateFeature(feature)
    else:
        # self.plugin_message_bar.pushMessage("Warning", f"Error with shortest_dist().", level=Qgis.Warning)
        raise ValueError("Error: Resulting layer from shortest line between features is not valid.")

    return result_layer


def retrieve_n_coordinate(f, shortest_dist_layer, info_dict):

    feature = shortest_dist_layer.getFeature(f.id())

    if feature.isValid():
        try:
            # Change the sign to negative according to which side of the centerline the point it located
            n_coordinate = feature['distance']
            if info_dict[f.id()]['side'] == -1:
                n_coordinate *= -1
        except (ValueError, TypeError) as e:
            print(f"Error processing n_coordinate for feature ID {f.id()}: {e}")
    else:
        print(f"No valid feature found with ID {f.id()}")

    return n_coordinate