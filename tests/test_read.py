import os
import unittest

import numpy as np

from hydrosurvey.sdi.binary import Dataset


class TestRead(unittest.TestCase):
    """ Test basic reading of binary files
    """

    def setUp(self):
        self.test_dir = os.path.dirname(__file__)

    def test_read(self):
        """ Test that all test files can be read without errors """
        for root, dirs, files in os.walk(os.path.join(self.test_dir, 'data', 'sdi')):
            for filename in files:
                if filename.endswith('.bin'):
                    d = Dataset(os.path.join(root, filename))
                    data = d.as_dict()
                    for freq_dict in data['frequencies']:
                        x = freq_dict['easting']
                        y = freq_dict['northing']
                        image = freq_dict['intensity']
                        self.assertIsInstance(x, np.ndarray)
                        self.assertIsInstance(y, np.ndarray)
                        self.assertIsInstance(image, np.ndarray)

    def test_fill_nans(self):
        """ Test for "IndexError: tuple index out of range"
        """
        filename = os.path.join(self.test_dir, 'data', 'sdi', '07050823.bin')
        d = Dataset(filename)
        data = d.as_dict()

    def test_overflowerror(self):
        """ Test for "OverflowError: Python int too large to convert to C long"
        """
        filename = os.path.join(self.test_dir, 'data', 'sdi', '09062409.bin')
        d = Dataset(filename)
        data = d.as_dict()

    def test_discontinuity(self):
        """ Test for "IndexError: index out of bounds"
        """
        filename = os.path.join(self.test_dir, 'data', 'sdi', '08091852.bin')
        d = Dataset(filename)
        data = d.as_dict()

    def test_separate_false(self):
        """ Test that separate=False works as expected
        """
        filename = os.path.join(self.test_dir, 'data', 'sdi', '07050823.bin')
        d = Dataset(filename)
        data = d.as_dict(separate=False)

        assert 'frequencies' not in data
        self.assertIsInstance(data['intensity'], np.ndarray)
        self.assertIsInstance(data['interpolated_easting'], np.ndarray)
        assert len(data['transducer']) == 3995
        assert len(np.unique(data['kHz'])) == 3

if __name__ == '__main__':
    unittest.main()
