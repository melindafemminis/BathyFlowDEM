
from qgis.core import QgsFeatureRequest, QgsSpatialIndexKDBush, QgsSpatialIndex

def create_index(point_layer):
    index =  QgsSpatialIndex(point_layer.getFeatures())
    return index

def create_indexKDBush(point_layer):
    index =  QgsSpatialIndexKDBush(point_layer.getFeatures())
    return index


def eidw(target_point, value_field, index, point_layer, anisotropy_ratio, max_distance, p):
        """Perform IDW interpolation using anisotropy along the already aligned S and N coordinates.

        Args:
            point_layer (QgsVectorLayer): Input layer with point features containing S, N, and Z.
            value_field (str): Name of the field with values to interpolate.
            target_s (float): Target point's S coordinate.
            target_n (float): Target point's N coordinate.
            anisotropy_ratio (float): Factor by which distances across the flow (N direction) are scaled.

        Returns:
            float: Interpolated value at the target location or 0 if no data
        """
        sum_weighted_values = 0
        sum_weights = 0
        distances = []
        target_s = target_point['S']
        target_n = target_point['N']

        # if usind the QgsSpatialIndex class, search is done by total number of neigbors
        """ nearest_ids = index.nearestNeighbor(target_point.geometry(), neighbors=100)
        nearest_features = [feature for feature in point_layer.getFeatures(QgsFeatureRequest().setFilterFids(nearest_ids))] """

        # if using the faster QgsSpatialIndexKDBuch class, search is done by radius
        nearest_data = index.within(target_point.geometry().asPoint(), radius=max_distance)
        nearest_ids = [data.id for data in nearest_data]
        # nearest_ids = index.within(target_point.geometry().asPoint(), radius=max_distance)
        nearest_features = [feature for feature in point_layer.getFeatures(QgsFeatureRequest().setFilterFids(nearest_ids))]
        
        for feature in nearest_features:
            s = feature['S']
            n = feature['N']
            value = feature[value_field]
            
            # Calculate distances in the S and N directions
            ds = s - target_s

            # Same to n but take into account negative numbers
            if target_n and n >= 0:
                dn1 = abs(target_n - n)
            elif target_n and n < 0: 
                dn1 = abs(target_n - n)
            else: 
                dn1 = abs(target_n) + abs(n)
            dn = dn1 * anisotropy_ratio

            # Calculate the anisotropic distance by modifying it on the N axis
            distance = (ds**2 + dn**2) ** 0.5

            if distance <= max_distance:
                distances.append((distance, value))
            
            if distance < 0.0001:  # If point is right on it/super close
                return value
                        
        if not distances:
            return 0
        else:
            for distance, value, in distances:
                weight = 1 / (distance ** p)
                sum_weights += weight
                sum_weighted_values += weight * value
            
            return sum_weighted_values / sum_weights