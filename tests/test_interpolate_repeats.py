import unittest

import numpy as np
from numpy import nan

from hydrosurvey.sdi.binary import _interpolate_repeats


class TestInterpolateRepeats(unittest.TestCase):
    """ Test _interpolate_repeats helper function
    """

    def test_monotonic(self):
        """Test that _interpolate_repeats works when the values are increasing
        monotonically.
        """
        repeats = np.array([
            1,
            1,
            1,
            2,
            2,
            3,
            3,
            3,
            4,
            4,
            5,
            5,
            5,
            5,
            6,
            6,
        ], dtype=np.float32)

        expected = np.array([
            1.,
            1.33333333,
            1.66666667,
            2.,
            2.5,
            3.,
            3.33333333,
            3.66666667,
            4.,
            4.5,
            5.,
            5.25,
            5.5,
            5.75,
            6.,
            6.25,
        ], dtype=np.float32)

        interpolated = _interpolate_repeats(repeats)

        np.testing.assert_allclose(interpolated, expected)

    def test_non_monotonic(self):
        """Test that _interpolate_repeats works when the values are not
        monotonic.
        """
        repeats = np.array([
            1,
            1,
            1,
            2,
            2,
            3,
            3,
            3,
            4,
            4,
            2,
            2,
            1,
            1,
            1,
            6,
        ], dtype=np.float32)

        expected = np.array([
            1.,
            1.33333333,
            1.66666667,
            2.,
            2.5,
            3.,
            3.33333333,
            3.66666667,
            4.,
            3.,
            2.,
            1.5,
            1.,
            2.66666667,
            4.33333333,
            6.,
        ], dtype=np.float32)

        interpolated = _interpolate_repeats(repeats)

        np.testing.assert_allclose(interpolated, expected)

    def test_with_nans(self):
        """Test that _interpolate_repeats interpolates with nans.
        """
        repeats = np.array([
            1,
            1,
            1,
            2,
            nan,
            4,
            4,
            7,
            7,
            7,
            nan,
            nan,
            nan,
            4,
            4,
        ], dtype=np.float32)

        expected = np.array([
            1.,
            1.33333333,
            1.66666667,
            2.,
            3.,
            4.,
            5.5,
            7.,
            6.5,
            6.,
            5.5,
            5.,
            4.5,
            4.,
            3.5,
        ], dtype=np.float32)

        interpolated = _interpolate_repeats(repeats)

        np.testing.assert_allclose(interpolated, expected)

    def test_with_nans_at_start(self):
        """Test that _interpolate_repeats interpolates with nans at the start.
        """
        repeats = np.array([
            nan,
            nan,
            nan,
            1,
            1,
            1,
            7,
        ], dtype=np.float32)

        expected = np.array([
            1,
            2,
            3,
            4,
            5,
            6,
            7,
        ], dtype=np.float32)

        interpolated = _interpolate_repeats(repeats)

        np.testing.assert_allclose(interpolated, expected)

    def test_with_nans_at_end(self):
        """Test that _interpolate_repeats interpolates with nans at the end.
        """
        repeats = np.array([
            1,
            1,
            1,
            4,
            nan,
            nan,
            nan,
        ], dtype=np.float32)

        expected = np.array([
            1,
            2,
            3,
            4,
            5,
            6,
            7,
        ], dtype=np.float32)

        interpolated = _interpolate_repeats(repeats)

        np.testing.assert_allclose(interpolated, expected)


if __name__ == '__main__':
    unittest.main()
