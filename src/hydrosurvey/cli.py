import os
import tomllib
from pathlib import Path
from typing import Optional

import geopandas as gpd
import hydrofunctions as hf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import panel as pn
import questionary
import rasterio
import tomli_w
import typer
import xarray as xr
from rich import print

from . import __version__, sdi
from .interpolate import aeidw

app = typer.Typer(
    help=f"Hydrosurvey Tools v{__version__}",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version_callback(value: bool):
    """
    Show the version of the hydrosurvey package.
    """
    if value:
        print(f"hydrosurvey version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
):
    """
    Hydrosurvey Tools
    """
    return


@app.command()
def write_xyz(
    path: Path, tide_file: str, output_file: str, usgs_parameter: str
):  # usgs_site, usgs_parameter):
    """Reads SDI binary and pick files and writes to xyz file."""
    path = Path(path)
    output_file = Path(output_file)
    data = []
    for sdi_file in list(path.rglob("*.bin")):
        print("=" * 40)
        print(f"Processing {sdi_file.stem}")
        print("_" * 40)
        print(f"... Reading bin file")
        try:
            s = sdi.binary.read(sdi_file, as_dataframe=True)
        except:
            print(f"... ERROR: Could not read {sdi_file.stem}")
            continue

        print(f"... Reading pic files")
        pic_files = list(path.rglob(f"{sdi_file.stem}*.pic"))
        if len(pic_files) == 0:
            print(f"... ERROR: No pic files found for {sdi_file.stem}")
            continue

        try:
            for pic_file in path.rglob(f"{sdi_file.stem}*.pic"):
                p = sdi.pickfile.read(pic_file, as_dataframe=True)
                s = pd.merge(
                    s, p, how="left", left_index=True, right_index=True
                ).reset_index()
        except:
            print(f"... ERROR: Could not read pic files for {sdi_file.stem}")
            continue

        data.append(s)
        print(f"... Done processing {sdi_file.stem} \n\n")

    print(f"Merging files \n\n")
    data = pd.concat(data)

    cols = [
        "datetime",
        "survey_line_number",
        "interpolated_easting",
        "interpolated_northing",
        "interpolated_longitude",
        "interpolated_latitude",
        "depth_r1",
    ] + [k for k in data.keys() if "depth_surface" in k]

    data = (
        data[cols]
        .sort_values(by="datetime")
        .dropna()
        .rename(columns={k: k.split("_")[-1] for k in cols if "interpolated" in k})
    ).set_index("datetime")

    # convert to feet
    for k in [k for k in data.keys() if "depth" in k]:
        data[k] = data[k] * 3.28084

    # get tide data
    metadata, tide, cols, _ = hf.usgs_rdb.read_rdb(open(tide_file, "r").read())
    tide = tide.set_index("datetime").rename(columns={usgs_parameter: "lake_elevation"})
    tide = tide[["lake_elevation"]]
    tide.index = pd.to_datetime(tide.index)

    # start_date = (data.datetime.min() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    # end_date = (data.datetime.max() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    # data = data.set_index("datetime").tz_localize("US/Central")

    # print(f"Downloading {usgs_parameter} data from USGS site {usgs_site}")
    # tide = hf.NWIS(
    #    site=usgs_site,
    #    service="iv",
    #    parameterCd=usgs_parameter,
    #    start_date=start_date,
    #    end_date=end_date,
    # )
    # tide = tide.df(usgs_parameter).tz_convert("US/Central")

    # tide.index.name = "datetime"
    # tide = tide.tz_convert("US/Central")

    print("Interpolating tide data to match survey data")
    merged = data.merge(tide, on="datetime", how="outer").sort_values("datetime")
    merged = merged.interpolate(method="index").dropna()
    print("Calculating surface elevations")
    merged["current_surface"] = merged["lake_elevation"] - merged["depth_surface_1"]
    if "depth_surface_2" in merged.columns:
        merged["pre_impoundment_surface"] = (
            merged["lake_elevation"] - merged["depth_surface_2"]
        )
        merged["sediment_thickness"] = (
            merged["depth_surface_2"] - merged["depth_surface_1"]
        )
    merged.to_csv(output_file)
    print(f"Done! Saved to {output_file}")


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

    survey_current_surface_elevation = questionary.select(
        "Choose survey surface elevation column", choices=choices
    ).ask()
    choices.remove(survey_current_surface_elevation)

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
    config["survey_points"][
        "current_surface_elevation_column"
    ] = survey_current_surface_elevation
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
    print(f"Writing interpolated elevations to file:")
    points_to_file(interpolated_points, config["output"]["filepath"])


@app.command()
def gui():
    """
    Launch the Hydrosurvey GUI.
    """
    print("Launching Hydrosurvey GUI")
    from .gui import template

    # Define a function to close the server
    def close_server():
        pn.state.kill_all_servers()
        print("Panel server stopped.")
        os._exit(0)  # Forcefully exit the process

    # Create a button to close the server
    shutdown_button = pn.widgets.Button(name="Close HSTools")
    shutdown_button.js_on_click(code="window.close();")
    shutdown_button.on_click(lambda event: close_server())

    # Add the shutdown button to the template (e.g., in the sidebar or main area)
    template.sidebar.append(pn.layout.Divider())
    template.sidebar.append(shutdown_button)

    pn.serve(template, show=True)


@app.command()
def compute_eac(
    raster_file: Path,
    output_file: Path,
    lake_elevation: Optional[float] = None,
    step_size: Optional[float] = 0.1,
    overide_nodata: Optional[float] = None,
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

    if overide_nodata:
        nodata = overide_nodata

    da = da.where(da != nodata)

    if not lake_elevation:
        lake_elevation = da.max(skipna=True).to_dataarray().values[0]

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
        plot_eac_curve(eac, output_file.with_suffix(".png"))

    fmt = "%1.2f, %1.4f, %1.4f"
    np.savetxt(
        output_file,
        eac,
        header="Elevation, Area, Capacity",
        delimiter=",",
        fmt=fmt,
    )
    print(f"EAC curve saved to {output_file}")


def plot_eac_curve(eac, output_file):
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
    plt.savefig(output_file)


def points_to_file(gdf: gpd.GeoDataFrame, output_file: str):

    output_file = Path(output_file)
    gdf = gdf.drop(columns=["id"])

    # Write to GeoPackage
    print(f"\t geopackage written to {output_file.with_suffix('.gpkg')}")
    gdf.to_file(output_file.with_suffix(".gpkg"), driver="GPKG")

    # write to Parquet
    print(f"\t geoparquet written to {output_file.with_suffix('.parquet')}")
    gdf.to_parquet(output_file.with_suffix(".parquet"))

    # write to CSV

    # Extract coordinates
    gdf["x_coordinate"] = gdf.geometry.x
    gdf["y_coordinate"] = gdf.geometry.y

    # Drop the geometry column and sort
    gdf = gdf.drop(columns=["geometry"])
    gdf = gdf.sort_values(by=["x_coordinate", "y_coordinate"])

    column_order = [
        "x_coordinate",
        "y_coordinate",
        "current_surface_elevation",
        "preimpoundment_elevation",
        "type",
        "source",
    ]

    print(f"\t csv written to {output_file.with_suffix('.csv')}")
    gdf.to_csv(output_file.with_suffix(".csv"), columns=column_order, index=False)


def is_python_file(path: str) -> bool:
    return path.endswith(".py")
