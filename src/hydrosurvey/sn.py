import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point


class Coord_SN:
    def __init__(
        self, centerline: gpd.GeoDataFrame, max_segment_length=10, slope_dx=0.01
    ):
        """
        Transform the centerline and points to the SN coordinate system.
        """

        cline = centerline.iloc[0]["geometry"]
        geometry = []
        data = []
        for s_coord in np.arange(0, cline.length, max_segment_length):
            point = cline.interpolate(s_coord)
            s1 = cline.interpolate(s_coord - slope_dx)
            s2 = cline.interpolate(s_coord + slope_dx)
            slope = [s2.x - s1.x, s2.y - s1.y]
            geometry.append(point)
            data.append({"s_coord": s_coord, "slope": slope})

        self.centerline = gpd.GeoDataFrame(
            data=data, geometry=geometry, crs=centerline.crs
        )

    def find_sign(self, row):
        pt = row["geometry"]
        pt_s = row["centerline_point"]
        slope = row["slope"]
        return -np.sign((slope[0] * (pt.y - pt_s.y) - slope[1] * (pt.x - pt_s.x)))

    def transform_xy_to_sn(self, points: gpd.GeoDataFrame):
        nearest_points = gpd.sjoin_nearest(
            points, self.centerline, distance_col="n_coord"
        ).rename(columns={"index_right": "centerline_index"})

        nearest_points["centerline_point"] = (
            self.centerline["geometry"]
            .loc[nearest_points["centerline_index"]]
            .to_list()
        )

        nearest_points["n_coord"] = (
            nearest_points.apply(lambda x: self.find_sign(x), axis=1)
            * nearest_points["n_coord"]
        )

        return nearest_points
