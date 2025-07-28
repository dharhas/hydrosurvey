import os
import unittest

import numpy as np

from hydrosurvey.sdi.binary import Dataset


class TestRead(unittest.TestCase):
    """ Test basic reading of binary files
    """

    def setUp(self):
        self.test_dir = os.path.dirname(__file__)

    def test_normalized_intensities(self):
        """ Test that normalized intensities lie in the interval [0,1] """
        for root, dirs, files in os.walk(os.path.join(self.test_dir, 'data', 'sdi')):
            for filename in files:
                if filename.endswith('.bin'):
                    d = Dataset(os.path.join(root, filename))
                    d.parse()
                    self.assertLessEqual(np.nanmax(d.intensity_image), np.float64(1))
                    self.assertGreaterEqual(np.nanmin(d.intensity_image), np.float64(0))


if __name__ == '__main__':
    unittest.main()