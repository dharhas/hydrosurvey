import os
import subprocess
import tomllib
from pathlib import Path
from typing import Optional

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import questionary
import rasterio
import tomli_w
import typer
import xarray as xr
from rich import print

from .interpolate import aeidw

app = typer.Typer(
    help="Hydrosurvey CLI",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.command()
def merge_xyz(input_folder: Path, output_file: str, folder_prefix: str = "Srf"):
    """
    Merge current and preimpoundment surface xyz files into a single csv file.

    Note: Does not do tidal corrections.
    """
    all_files = [x for x in input_folder.rglob("*.xyz") if folder_prefix in str(x)]

    current_surface = pd.concat(
        [
            pd.read_csv(
                f, names=["x_coord", "y_coord", "current_surface_z"], sep=r"\s+"
            )
            for f in all_files
            if str(f).endswith("_1.xyz")
        ],
        ignore_index=True,
    )

    preimpoundment_surface = pd.concat(
        [
            pd.read_csv(f, names=["x_coord", "y_coord", "preimpoundment_z"], sep=r"\s+")
            for f in all_files
            if str(f).endswith("_2.xyz")
        ],
        ignore_index=True,
    )

    current_surface["preimpoundment_z"] = preimpoundment_surface["preimpoundment_z"]

    current_surface.to_csv(output_file, index=False)
    print(f"Merged file saved to {output_file}")


# @app.command()
# def download_usgs_data(usgs_site: str, start_date: str, end_date: str):
#    raise NotImplementedError("This function is not implemented yet.")
#    print(f"Downloading USGS data for {usgs_site} from {start_date} to {end_date}")


@app.command()
def new_config(configfile: Optional[Path]):
    """
    Generate a new configuration file for AEIDW lake interpolation.
    """
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
    crs = gpd.read_file(boundary_file, rows=0).crs.to_string()
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

    survey_crs = questionary.text("Enter Survey CRS", default=crs).ask()

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


@app.command()
def interpolate_lake(configfile: Optional[Path]):
    """
    Interpolate lake elevations using the AEIDW method.
    """
    with open(configfile, "rb") as f:
        config = tomllib.load(f)
    print(config)
    interpolated_points = aeidw(config)

    # write out the interpolated elevations
    print(f"Writing interpolated elevations to {config['output']['filepath']}")
    points_to_csv(interpolated_points, config["output"]["filepath"])


@app.command()
def gui():
    """
    Launch the Hydrosurvey GUI.
    """
    print("Launching Hydrosurvey GUI")
    # this is hacky but works for now
    p = Path(os.path.abspath(__file__)).parent
    subprocess.run(["panel", "serve", str(p.joinpath("gui.py")), "--show"])


@app.command()
def compute_eac(
    raster_file: Path,
    output_file: Path,
    lake_elevation: Optional[float] = None,
    step_size: Optional[float] = None,
    nodata: Optional[float] = None,
    # plot_areas: Optional[bool] = None,
    plot_curve: Optional[bool] = None,
):
    """
    Calculates elevation-area-capacity curve from lake DEM in tiff format.
    """
    da = xr.open_dataset(raster_file, engine="rasterio")
    with rasterio.open(raster_file) as src:
        pixel_dx, pixel_dy = src.res
        nodata = src.nodata

    pixel_area = pixel_dx * pixel_dy

    if not nodata:
        nodata = -9999.0

    da = da.where(da != nodata)

    if not lake_elevation:
        lake_elevation = da.max(skipna=True).to_dataarray().values[0]

    if not step_size:
        step_size = 0.1

    lowest_elevation = da.min(skipna=True).to_dataarray().values[0]
    eac = []

    # make elevation intevals clean numbers
    e1 = (np.floor(lake_elevation / step_size) * step_size).round(decimals=2)
    elevations = np.arange(e1, lowest_elevation, -step_size)
    elevations = np.insert(elevations, 0, lake_elevation)

    # get rid of extra elevation caused by floating point precision issues
    if np.abs(elevations[-1] - lowest_elevation) < 0.005:
        elevations[-1] = lowest_elevation

    # make sure lowest point is included
    if elevations[-1] > lowest_elevation:
        elevations = np.append(elevations, lowest_elevation)

    # Calculate Area & Volume for each elevation
    for elev in elevations:
        # mask all pixels where depth from elevation is negative
        depths = elev - da
        depths = depths.where(depths >= 0)
        # compute area and volume
        area = depths.notnull().sum() * pixel_area
        volume = depths.sum() * pixel_area
        eac.append(
            [
                elev,
                area.to_dataarray().values[0],
                volume.to_dataarray().values[0],
            ]
        )

        # if plot_areas:
        #    da.plot(aspect=1, size=8)
        #    #    plt.title("Lake at %s Elevation" % elev)
        #    plt.savefig("lake_at_%s.png" % elev)
        #    plt.close()

    eac = np.array(eac)
    if plot_curve:
        plot_eac_curve(eac)

    fmt = "%1.2f, %1.4f, %1.4f"
    np.savetxt(
        output_file,
        eac,
        header="Elevation, Area, Capacity",
        delimiter=",",
        fmt=fmt,
    )
    print(f"EAC curve saved to {output_file}")


def plot_eac_curve(eac):
    fig, ax1 = plt.subplots()
    ax1.plot(eac[:, 1], eac[:, 0], "b")
    ax1.set_ylabel("Elevation")
    # Make the y-axis label, ticks and tick labels match the line color.
    ax1.set_xlabel("Area", color="b")
    ax1.tick_params("x", colors="b")

    ax2 = ax1.twiny()
    ax2.plot(eac[:, 2], eac[:, 0], "r")
    ax2.set_xlabel("Capacity", color="r")
    ax2.tick_params("x", colors="r")
    ax2.set_xlim(ax2.get_xlim()[::-1])

    fig.tight_layout()
    plt.savefig("elevation_area_capacity.png")


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
