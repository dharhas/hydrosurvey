import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon
from tqdm import tqdm


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


def generate_target_points(polygons: gpd.GeoDataFrame):
    """
    Generate target interpolation points.
    """
    masked = {}
    for idx, _ in tqdm(
        polygons.iterrows(),
        total=polygons.shape[0],
        desc="Generating target interpolation points for each polygon",
    ):
        priority = polygons.loc[idx]["priority"]
        resolution = polygons.loc[idx]["gridspace"]
        grid = polygon_to_mesh(polygons.loc[[idx]], resolution)
        higher_priority = polygons.loc[polygons["priority"] < priority]
        masked[idx] = mask_higher_priority_polygons(grid, higher_priority)

    return gpd.GeoDataFrame(
        pd.concat(masked, ignore_index=True), crs=masked[next(iter(masked))].crs
    )


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


def read_lake_data(config: dict):
    """
    Read the data from the configuration file.
    """
    boundary = gpd.read_file(config["boundary"]["filepath"]).rename(
        columns={config["boundary"]["elevation_column"]: "elevation"}
    )[["elevation", "geometry"]]

    lines = gpd.read_file(config["interpolation_centerlines"]["filepath"]).set_index(
        config["interpolation_centerlines"]["polygon_id_column"]
    )[["geometry"]]

    polygons = (
        gpd.read_file(config["interpolation_polygons"]["filepath"])
        .set_index(config["interpolation_polygons"]["polygon_id_column"])
        .rename(
            columns={
                config["interpolation_polygons"]["grid_spacing_column"]: "gridspace",
                config["interpolation_polygons"]["priority_column"]: "priority",
                config["interpolation_polygons"][
                    "interpolation_method_column"
                ]: "method",
                config["interpolation_polygons"][
                    "interpolation_params_column"
                ]: "params",
            }
        )
    )[["priority", "gridspace", "method", "params", "geometry"]]

    # Read the survey points CSV file
    columns = {
        config["survey_points"]["x_coord_column"]: "x_coord",
        config["survey_points"]["y_coord_column"]: "y_coord",
        config["survey_points"]["surface_elevation_column"]: "surface_elevation",
    }

    if config["survey_points"].get("preimpoundment_elevation_column"):
        columns.update(
            {
                config["survey_points"][
                    "preimpoundment_elevation_column"
                ]: "preimpoundment_elevation"
            }
        )

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(
        config["survey_points"]["filepath"], usecols=columns.keys()
    ).rename(columns=columns)

    # return df
    # Create a geometry column from the longitude and latitude columns
    geometry = [Point(xy) for xy in zip(df["x_coord"], df["y_coord"])]

    # Create a GeoDataFrame
    survey_points = gpd.GeoDataFrame(
        df, geometry=geometry, crs=config["survey_points"]["crs"]
    ).drop(columns=["x_coord", "y_coord"])

    return boundary, lines, polygons, survey_points


def aeidw(config: dict):
    """
    Interpolate the survey points.
    """

    # densify boundary, and centerlines - done
    # add boundary points + elevations to survey_points - done
    # generate meshes for each polygon --- need to add boundary mask as well by clipping - deone

    # loop through each polygon
    # .. convert the mesh and survery_points to SN coordinates
    # .. choose interpolation type
    # .. apply ellipsivity factor
    # .. interpolate the elevations with idw
    # write out files

    # read files
    boundary, lines, polygons, survey_points = read_lake_data(config)

    dense_boundary = densify_geometry(
        boundary, max_segment_length=config["boundary"]["max_segment_length"]
    )
    dense_centerlines = densify_geometry(
        lines,
        max_segment_length=config["interpolation_centerlines"]["max_segment_length"],
    )

    # add lake boundary elevations to survey_points
    xy = dense_boundary.iloc[0]["geometry"].exterior.coords.xy
    boundary_points = gpd.GeoDataFrame(
        gpd.GeoSeries(
            gpd.points_from_xy(x=xy[0], y=xy[1]), crs=boundary.crs, name="geometry"
        )
    )
    boundary_points["surface_elevation"] = boundary.iloc[0]["elevation"]
    survey_points = gpd.GeoDataFrame(
        pd.concat(
            [survey_points, boundary_points],
            ignore_index=True,
        ),
        crs=survey_points.crs,
    )

    # generate target interpolation points
    target_points = generate_target_points(polygons)

    # remove points outside the boundary or within islands
    target_points = target_points.clip(boundary)

    # transform the centerlines and
