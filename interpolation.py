def eidw(target_s, target_n, value_field, point_layer, anisotropy_ratio, max_distance):
        """
        Perform IDW interpolation using anisotropy along the already aligned S and N coordinates.

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
        
        for feature in point_layer.getFeatures():
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
                weight = 1 / distance
                sum_weights += weight
                sum_weighted_values += weight * value
            
            return sum_weighted_values / sum_weights