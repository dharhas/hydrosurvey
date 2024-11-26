import numpy as np
from scipy.interpolate import splev, splprep
from shapely.geometry import LineString, Point


class Coord_SN:
    """
    Convert x,y,z dataset into SN Coordinate System based on a given centerline.
    """

    def __init__(self, cx, cy, slope_distance=0.01):
        """
        Initialize SN coordinate system. Requires arrays containing cartesian x,y values
        and arrays containing centerline cx,cy cartesian coordinates
        """
        cx, cy = self.smooth_cline(cx, cy, interp, interp_params)
        self.cline = LineString(list(zip(cx.tolist(), cy.tolist())))
        self.slope_distance = slope_distance

    def transform_xy_to_sn(self, x, y):
        s = np.zeros(x.size)
        n = np.zeros(x.size)
        v = np.zeros((x.size, 2))
        vn = np.zeros((x.size, 2))
        for ii in range(x.size):
            pt = Point((x[ii], y[ii]))
            s[ii] = self.cline.project(pt)
            pt_s = self.cline.interpolate(s[ii])
            pt_s1 = self.cline.interpolate(s[ii] - self.slope_distance)
            pt_s2 = self.cline.interpolate(s[ii] + self.slope_distance)
            vn[ii, 0] = pt.x - pt_s.x
            vn[ii, 1] = pt.y - pt_s.y
            v[ii, 0] = pt_s2.x - pt_s1.x
            v[ii, 1] = pt_s2.y - pt_s1.y
            n[ii] = pt_s.distance(pt)

        n = -np.sign(np.cross(v, vn)) * n
        return (s, n)
