import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon


def polygon_to_mesh(polygon: gpd.GeoDataFrame, resolution: float):
    """
    Convert a polygon to a mesh.
    """
    # Get the bounding box of the polygon
    minx, miny, maxx, maxy = polygon.total_bounds

    # Create the x and y coordinates of the grid
    x = np.arange(minx, maxx, resolution)
    y = np.arange(miny, maxy, resolution)

    # Create the meshgrid
    xx, yy = np.meshgrid(x, y)

    points = gpd.points_from_xy(x=xx.flatten(), y=yy.flatten())
    grid = gpd.GeoDataFrame(gpd.GeoSeries(points, crs=polygon.crs, name="geometry"))

    return gpd.sjoin(grid, polygon[["geometry"]], how="inner").rename(
        columns={"index_right": "polygon_id"}
    )


def mask_higher_priority_polygons(
    points: gpd.GeoDataFrame, higher_priority: gpd.GeoDataFrame
):
    """
    Mask the higher priority polygon with the lower priority polygon.
    """
    return gpd.overlay(points, higher_priority, how="difference")


def generate_interpolation_points(polygons: gpd.GeoDataFrame):
    """
    Generate interpolation points.
    """
    for polygon in polygons:
        yield from polygon_to_mesh(polygon, resolution=10)


def generate_interpolation_points(polygons: gpd.GeoDataFrame):
    """
    Generate interpolation lines.
    """
    masked = {}
    for idx, _ in polygons.iterrows():
        priority = polygons.loc[idx]["Prior"]
        resolution = polygons.loc[idx]["Gridspace"]
        grid = polygon_to_mesh(sorted_polygons.loc[[idx]], resolution)
        higher_priority = polygons.loc[polygons["Prior"] < priority]
        masked[idx] = mask_higher_priority_polygons(grid, higher_priority)

    return gpd.GeoDataFrame(pd.concat(masked, ignore_index=True), crs=masked[0].crs)


def densify_geometry(gdf: gpd.GeoDataFrame, max_segment_length=10):
    dense_gdf = gdf.copy()
    dense_gdf["geometry"] = dense_gdf.segmentize(max_segment_length)
    return dense_gdf


def transform_to_sn_coords_new(centerline: gpd.GeoDataFrame, points: gpd.GeoDataFrame):
    """
    Transform the centerline and points to the SN coordinate system.
    """

    # centerline = densify_geometry(centerline) # do this outside this function

    # extract points from the centerline
    # points = centerline["geometry"].coords

    centerline_points = np.array(centerline["geometry"].coords.xy).T

    # Calculate `S` the cumulative distance along the centerline
    # ----------------------------------------------------------

    # Calculate the differences between consecutive points
    diffs = np.diff(centerline_points, axis=0)

    # Calculate the perpendicular distances between the centerline and the points
    distances = np.zeros(len(centerline_points))
    distances[1:] = np.sqrt(np.sum(diffs**2, axis=1)).cumsum()

    # Calculate the normal distance between each point and the closest centerline point
    # ---------------------------------------------------------------------------------

    centerline_points_gdf = gpd.GeoDataFrame(
        gpd.GeoSeries(
            gpd.points_from_xy(x=centerline.coords.xy[0], y=centerline.coords.xy[1]),
            crs=centerline.crs,
            name="geometry",
        )
    )

    nearest_points = gpd.sjoin_nearest(
        points, centerline_points_gdf, distance_col="n_coord"
    ).rename(columns={"index_right": "centerline_index"})

    nearest_points["s_coord"] = distances[nearest_points["centerline_index"]]
    nearest_points["n_coord"] = nearest_points["n_coord"] * np.sign(
        nearest_points["s_coord"]
    )

    return nearest_points


def interpolate(boundary, centerlines, polygons, survey_points):
    """
    Interpolate the survey points.
    """

    # densify boundary, and centerlines
    # add boundary points + elevations to survey_points
    # generate meshes for each polygon --- need to add boundary mask as well by clipping

    # loop through each polygon
    # .. convert the mesh and survery_points to SN coordinates
    # .. choose interpolation type
    # .. apply ellipsivity factor
    # .. interpolate the elevations with idw
    # write out files

    pass
