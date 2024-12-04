import numpy as np
from scipy.spatial import cKDTree


def idw(coords, values, query_points, nnear=16, power=2):
    """
    Perform Inverse Distance Weighting interpolation.

    Parameters:
        coords (np.ndarray): Array of coordinates for known data points (shape: N, D)
        values (np.ndarray): Array of values at known data points (shape: N, C)
        query_points (np.ndarray): Array of coordinates for query points (shape: M, D)
        power (float): Exponent for the inverse distance weighting (default: 2)

    Returns:
        np.ndarray: Array of interpolated values at query points (shape: M, C)
    """

    tree = cKDTree(coords)
    distances, indices = tree.query(query_points, k=nnear)

    # Calculate weights
    weights = 1.0 / (distances + 1e-10) ** power

    # Normalize weights
    weights /= weights.sum(axis=1, keepdims=True)

    # Interpolate each column separately
    interpolated_values = np.zeros((query_points.shape[0], values.shape[1]))
    for i in range(values.shape[1]):
        interpolated_values[:, i] = np.sum(weights * values[indices, i], axis=1)

    return interpolated_values
