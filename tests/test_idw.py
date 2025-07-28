import unittest

import numpy as np
import numpy.testing as npt

from hydrosurvey.methods import idw


class TestIDW(unittest.TestCase):
    """Test the Inverse Distance Weighting (IDW) interpolation function."""

    def setUp(self):
        """Set up test data."""
        # Simple 2D grid of known points
        self.coords_2d = np.array([
            [0.0, 0.0],
            [1.0, 0.0], 
            [0.0, 1.0],
            [1.0, 1.0]
        ])
        
        # Single column of values
        self.values_single = np.array([
            [0.0],
            [1.0],
            [2.0], 
            [3.0]
        ])
        
        # Multiple columns of values
        self.values_multi = np.array([
            [0.0, 10.0],
            [1.0, 11.0],
            [2.0, 12.0],
            [3.0, 13.0]
        ])

    def test_exact_match_single_value(self):
        """Test that IDW returns exact values when query point matches known point."""
        query_points = np.array([[0.0, 0.0]])
        result = idw(self.coords_2d, self.values_single, query_points, nnear=4)
        npt.assert_allclose(result, [[0.0]], atol=1e-15)

    def test_exact_match_multiple_values(self):
        """Test exact match with multiple value columns."""
        query_points = np.array([[1.0, 1.0]])
        result = idw(self.coords_2d, self.values_multi, query_points, nnear=4)
        npt.assert_allclose(result, [[3.0, 13.0]], atol=1e-15)

    def test_center_interpolation(self):
        """Test interpolation at the center of a square grid."""
        query_points = np.array([[0.5, 0.5]])
        result = idw(self.coords_2d, self.values_single, query_points, power=2, nnear=4)
        
        # At the center, all points are equidistant, so result should be the average
        expected = np.mean(self.values_single)
        npt.assert_allclose(result, [[expected]], rtol=1e-6)

    def test_different_power_values(self):
        """Test that different power values produce different results."""
        query_points = np.array([[0.3, 0.7]])
        
        result_power1 = idw(self.coords_2d, self.values_single, query_points, power=1, nnear=4)
        result_power2 = idw(self.coords_2d, self.values_single, query_points, power=2, nnear=4)
        result_power3 = idw(self.coords_2d, self.values_single, query_points, power=3, nnear=4)
        
        # Results should be different for different power values
        self.assertFalse(np.allclose(result_power1, result_power2))
        self.assertFalse(np.allclose(result_power2, result_power3))

    def test_nnear_parameter(self):
        """Test that nnear parameter limits the number of neighbors used."""
        # Create more points than we'll use for interpolation
        coords = np.random.rand(20, 2)
        values = np.random.rand(20, 1)
        query_points = np.array([[0.5, 0.5]])
        
        # Test with different nnear values
        result_2 = idw(coords, values, query_points, nnear=2)
        result_5 = idw(coords, values, query_points, nnear=5)
        result_10 = idw(coords, values, query_points, nnear=10)
        
        # Results should be different when using different numbers of neighbors
        self.assertFalse(np.allclose(result_2, result_5))
        self.assertFalse(np.allclose(result_5, result_10))

    def test_multiple_query_points(self):
        """Test interpolation with multiple query points."""
        query_points = np.array([
            [0.25, 0.25],
            [0.75, 0.75],
            [0.5, 0.0]
        ])
        
        result = idw(self.coords_2d, self.values_single, query_points, nnear=4)
        
        # Check that we get the correct number of results
        self.assertEqual(result.shape, (3, 1))
        
        # All results should be finite
        self.assertTrue(np.all(np.isfinite(result)))

    def test_1d_coordinates(self):
        """Test IDW with 1D coordinates."""
        coords_1d = np.array([[0.0], [1.0], [2.0], [3.0]])
        values_1d = np.array([[0.0], [1.0], [4.0], [9.0]])  # y = x^2
        query_points_1d = np.array([[1.5]])
        
        result = idw(coords_1d, values_1d, query_points_1d, nnear=4)
        
        # Result should be between 1 and 4 (values at x=1 and x=2)
        self.assertTrue(1.0 <= result[0, 0] <= 4.0)

    def test_3d_coordinates(self):
        """Test IDW with 3D coordinates."""
        coords_3d = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        values_3d = np.array([[1.0], [2.0], [3.0], [4.0]])
        query_points_3d = np.array([[0.25, 0.25, 0.25]])
        
        result = idw(coords_3d, values_3d, query_points_3d, nnear=4)
        
        # Should get a valid result
        self.assertEqual(result.shape, (1, 1))
        self.assertTrue(np.isfinite(result[0, 0]))

    def test_linear_gradient(self):
        """Test IDW on a linear gradient."""
        # Create points along a line with linear values
        coords = np.array([[i, 0.0] for i in range(5)])
        values = np.array([[float(i)] for i in range(5)])
        
        # Query point in the middle
        query_points = np.array([[2.0, 0.0]])
        result = idw(coords, values, query_points, nnear=5)
        
        # Should be very close to 2.0 (exact for this linear case)
        npt.assert_allclose(result, [[2.0]], atol=1e-15)

    def test_weight_normalization(self):
        """Test that weights are properly normalized."""
        query_points = np.array([[0.1, 0.1]])
        result = idw(self.coords_2d, self.values_single, query_points, nnear=4)
        
        # Result should be a weighted average, so within range of input values
        min_val = np.min(self.values_single)
        max_val = np.max(self.values_single)
        self.assertTrue(min_val <= result[0, 0] <= max_val)

    def test_zero_distance_handling(self):
        """Test that zero distances are handled properly (no division by zero)."""
        # This is handled by adding a small epsilon (1e-10) in the implementation
        query_points = np.array([[0.0, 0.0]])  # Exact match
        result = idw(self.coords_2d, self.values_single, query_points, nnear=4)
        
        # Should not raise an error and should give exact value
        npt.assert_allclose(result, [[0.0]], atol=1e-15)

    def test_edge_cases(self):
        """Test edge cases."""
        # Test with minimum number of points (2) to avoid axis issues
        coords_minimal = np.array([[0.0, 0.0], [1.0, 1.0]])
        values_minimal = np.array([[5.0], [6.0]])
        query_points = np.array([[2.0, 2.0]])
        
        result = idw(coords_minimal, values_minimal, query_points, nnear=2)
        # Should be finite and reasonable
        self.assertTrue(np.all(np.isfinite(result)))
        self.assertTrue(5.0 <= result[0, 0] <= 7.0)  # Should be close to but can extrapolate beyond 6.0

    def test_input_shapes(self):
        """Test that function handles various input shapes correctly."""
        # Test with different numbers of dimensions and value columns
        coords = np.random.rand(10, 2)
        values_1col = np.random.rand(10, 1)
        values_3col = np.random.rand(10, 3)
        query_points = np.random.rand(5, 2)
        
        result_1col = idw(coords, values_1col, query_points, nnear=10)
        result_3col = idw(coords, values_3col, query_points, nnear=10)
        
        self.assertEqual(result_1col.shape, (5, 1))
        self.assertEqual(result_3col.shape, (5, 3))


if __name__ == "__main__":
    unittest.main()