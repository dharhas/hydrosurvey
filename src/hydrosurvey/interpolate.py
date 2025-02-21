import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm

from .methods import idw
from .sn import Coord_SN


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
        priority = polygons["priority"].loc[idx]
        resolution = polygons["gridspace"].loc[idx]
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
        gpd.read_file(config["interpolation_polygons"]["filepath"]).rename(
            columns={
                config["interpolation_polygons"]["polygon_id_column"]: "id",
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
    )[["id", "priority", "gridspace", "method", "params", "geometry"]].set_index("id")

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

    # add lake boundary elevations to survey_points
    boundary_x = []
    boundary_y = []
    x, y = dense_boundary.iloc[0]["geometry"].exterior.coords.xy
    boundary_x.append(x)
    boundary_y.append(y)
    for interior in dense_boundary.iloc[0]["geometry"].interiors:
        x, y = interior.coords.xy
        boundary_x.append(x)
        boundary_y.append(y)

    boundary_points = gpd.GeoDataFrame(
        gpd.GeoSeries(
            gpd.points_from_xy(
                x=np.concatenate(boundary_x), y=np.concatenate(boundary_y)
            ),
            crs=boundary.crs,
            name="geometry",
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

    for idx, _ in tqdm(
        polygons.iterrows(),
        total=polygons.shape[0],
        desc="Interpolating each polygon",
    ):
        method = polygons["method"].loc[idx]
        params = polygons["params"].loc[idx]

        # interpolate the elevations
        if method.lower() == "aeidw":
            # get the centerline for the polygon
            centerline = lines.loc[[idx]]
            source_points = survey_points.clip(
                polygons.loc[[idx]].buffer(config["interpolation_polygons"]["buffer"])
            )

            target_idx = target_points["id"] == idx
            if target_idx.empty:
                print(f"Polygon id {idx} not found in target_points")
                continue

            # transform the survey_points and target points to SN coordinates
            sn_transform = Coord_SN(centerline)
            source_points_sn = sn_transform.transform_xy_to_sn(source_points)
            target_points_sn = sn_transform.transform_xy_to_sn(
                target_points[target_idx]
            )

            # apply ellipsivity factor
            source_points_sn["n_coord"] = source_points_sn["n_coord"] * params
            target_points_sn["n_coord"] = target_points_sn["n_coord"] * params

            # interpolate the elevations
            if "preimpoundment_elevation" in source_points_sn.columns:
                columns = ["surface_elevation", "preimpoundment_elevation"]
            else:
                columns = ["surface_elevation"]

            new_elevs = idw(
                coords=source_points_sn[["s_coord", "n_coord"]].to_numpy(),
                values=source_points_sn[columns].to_numpy(),
                query_points=target_points_sn[["s_coord", "n_coord"]].to_numpy(),
                nnear=config["interpolation_polygons"].get("nearest_neighbors", 16),
            )

            # add the interpolated elevations to the target_points
            target_points.loc[target_idx, "surface_elevation"] = new_elevs[:, 0]
            if "preimpoundment_elevation" in source_points_sn.columns:
                target_points.loc[target_idx, "preimpoundment_elevation"] = new_elevs[
                    :, 1
                ]
        else:
            print(f"Interpolation method {method} not recognized for polygon id {idx}")

    # concatenate the survey points and target points
    all_points = gpd.GeoDataFrame(
        pd.concat([survey_points, target_points], ignore_index=True),
        crs=survey_points.crs,
    )
    return all_points
