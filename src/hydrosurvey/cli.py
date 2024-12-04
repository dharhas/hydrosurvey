import os
import tomllib
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import questionary
import tomli_w
import typer
from rich import print

from .interpolate import aeidw

app = typer.Typer(
    help="Hydrosurvey CLI",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command()
def sdi_to_csv(input_file: str, output_file: str):
    raise NotImplementedError("This function is not implemented yet.")
    print(f"Converting {input_file} to {output_file}")


@app.command()
def download_usgs_data(usgs_site: str, start_date: str, end_date: str):
    raise NotImplementedError("This function is not implemented yet.")
    print(f"Downloading USGS data for {usgs_site} from {start_date} to {end_date}")


@app.command()
def interpolate_lake(configfile: Optional[Path]):
    with open(configfile, "rb") as f:
        config = tomllib.load(f)
    print(config)
    interpolated_points = aeidw(config)

    # write out the interpolated elevations
    print(f"Writing interpolated elevations to {config['output']['filepath']}")
    points_to_csv(interpolated_points, config["output"]["filepath"])


@app.command()
def calculate_eac(name: str):
    raise NotImplementedError("This function is not implemented yet.")


def points_to_csv(gdf: gpd.GeoDataFrame, output_file: str):
    # Extract coordinates
    gdf["x_coordinate"] = gdf.geometry.x
    gdf["y_coordinate"] = gdf.geometry.y

    # Drop the geometry column
    gdf = gdf.drop(columns="geometry")

    # Write to CSV
    print(f"Writing DataFrame to {output_file}")
    gdf.to_csv(output_file, index=False)


def is_python_file(path: str) -> bool:
    return path.endswith(".py")


@app.command()
def create_config(configfile: Optional[Path]):
    config = {}

    # read lake metadata
    ############################

    lake = questionary.text("Enter Lake Name").ask()
    survey_year = questionary.text("Enter Survey Year").ask()
    config["lake"] = {}
    config["lake"]["name"] = lake
    config["lake"]["survey_year"] = int(survey_year)

    # read boundary
    ############################
    boundary_file = questionary.path(
        "Enter Boundary Shapefile",
        file_filter=lambda p: p.endswith("shp") or os.path.isdir(p),
    ).ask()

    # read boundary file to get column names
    print(gpd.read_file(boundary_file).columns)
    boundary_elevation_column = questionary.select(
        "Choose Boundary Elevation Column",
        choices=gpd.read_file(boundary_file, rows=0).columns.tolist(),
    ).ask()
    boundary_max_segment_length = questionary.text(
        "Enter Max Boundary Segment Length", default="10"
    ).ask()

    config["boundary"] = {}
    config["boundary"]["filepath"] = str(Path(boundary_file).absolute())
    config["boundary"]["elevation_column"] = boundary_elevation_column
    config["boundary"]["max_segment_length"] = int(boundary_max_segment_length)

    # read survey points
    ############################

    survey_points_file = questionary.path(
        "Enter Survey Points CSV File",
        file_filter=lambda p: p.endswith("csv") or os.path.isdir(p),
    ).ask()
    choices = pd.read_csv(survey_points_file, nrows=0).columns.tolist()
    survey_x_coord = questionary.select(
        "Choose survey x-coord column", choices=choices
    ).ask()
    choices.remove(survey_x_coord)

    survey_y_coord = questionary.select(
        "Choose survey y-coord column", choices=choices
    ).ask()
    choices.remove(survey_y_coord)

    survey_surface_elevation = questionary.select(
        "Choose survey surface elevation column", choices=choices
    ).ask()
    choices.remove(survey_surface_elevation)

    has_preimpoundment = questionary.confirm(
        "Does the survey have preimpoundment data?"
    ).ask()
    if has_preimpoundment:
        survey_preimpoundment_elevation = questionary.select(
            "Choose survey preimpoundment elevation column", choices=choices
        ).ask()
    else:
        survey_preimpoundment_elevation = ""

    survey_crs = questionary.text("Enter Survey CRS").ask()

    config["survey_points"] = {}
    config["survey_points"]["filepath"] = str(Path(survey_points_file).absolute())
    config["survey_points"]["x_coord_column"] = survey_x_coord
    config["survey_points"]["y_coord_column"] = survey_y_coord
    config["survey_points"]["surface_elevation_column"] = survey_surface_elevation
    config["survey_points"][
        "preimpoundment_elevation_column"
    ] = survey_preimpoundment_elevation
    config["survey_points"]["crs"] = survey_crs

    # read centerlines
    ############################

    centerlines_file = questionary.path(
        "Enter Centerlines File",
        file_filter=lambda p: p.endswith("shp") or os.path.isdir(p),
    ).ask()
    centerline_id_column = questionary.select(
        "Choose Polygon ID Column",
        choices=gpd.read_file(centerlines_file, rows=0).columns,
    ).ask()
    centerline_max_segment_length = questionary.text(
        "Enter Max Centerline Segment Length", default="10"
    ).ask()
    config["interpolation_centerlines"] = {}
    config["interpolation_centerlines"]["filepath"] = str(
        Path(centerlines_file).absolute()
    )
    config["interpolation_centerlines"]["polygon_id_column"] = centerline_id_column
    config["interpolation_centerlines"]["max_segment_length"] = int(
        centerline_max_segment_length
    )

    # read interpolations polygons
    ############################

    polygons_file = questionary.path(
        "Enter Polygons Shapefile",
        file_filter=lambda p: p.endswith("shp") or os.path.isdir(p),
    ).ask()
    choices = gpd.read_file(polygons_file, rows=0).columns.tolist()
    polygon_id_column = questionary.select(
        "Choose Polygon ID Column", choices=choices
    ).ask()
    choices.remove(polygon_id_column)
    polygon_grid_spacing_column = questionary.select(
        "Choose Grid Spacing Column", choices=choices
    ).ask()
    choices.remove(polygon_grid_spacing_column)
    polygon_priority_column = questionary.select(
        "Choose Priority Column", choices=choices
    ).ask()
    choices.remove(polygon_priority_column)
    polygon_interpolation_method_column = questionary.select(
        "Choose Interpolation Method Column", choices=choices
    ).ask()
    choices.remove(polygon_interpolation_method_column)
    polygon_interpolation_params_column = questionary.select(
        "Choose Interpolation Params Column", choices=choices
    ).ask()
    buffer = questionary.text("Enter Polygon Buffer Distance", default="100").ask()
    nearest_neighbors = questionary.text(
        "Enter Number of Nearest Neighbors for IDW", default="16"
    ).ask()

    config["interpolation_polygons"] = {}
    config["interpolation_polygons"]["filepath"] = str(Path(polygons_file).absolute())
    config["interpolation_polygons"]["polygon_id_column"] = polygon_id_column
    config["interpolation_polygons"][
        "grid_spacing_column"
    ] = polygon_grid_spacing_column
    config["interpolation_polygons"]["priority_column"] = polygon_priority_column
    config["interpolation_polygons"][
        "interpolation_method_column"
    ] = polygon_interpolation_method_column
    config["interpolation_polygons"][
        "interpolation_params_column"
    ] = polygon_interpolation_params_column
    config["interpolation_polygons"]["buffer"] = int(buffer)
    config["interpolation_polygons"]["nearest_neighbors"] = int(nearest_neighbors)

    # read output
    ############################
    output_file = questionary.path("Enter output File for interpolated points").ask()
    config["output"] = {}
    config["output"]["filepath"] = str(Path(output_file).absolute())

    # write config file
    ############################
    with open(configfile, "wb") as f:
        tomli_w.dump(config, f)

    print(f"Configuration file written to {configfile}")
