import tomllib
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import typer
from rich import print
from shapely.geometry import Point

app = typer.Typer()


@app.command()
def sdi_to_csv(input_file: str, output_file: str):
    print(f"Converting {input_file} to {output_file}")


@app.command()
def download_usgs_data(usgs_site: str, start_date: str, end_date: str):
    print(f"Downloading USGS data for {usgs_site} from {start_date} to {end_date}")


@app.command()
def interpolate_lake(config: Optional[Path]):
    with open(config, "rb") as f:
        config = tomllib.load(f)
    print(config)

    boundary = gpd.read_file(config["boundary"]["filepath"])
    lines = gpd.read_file(config["interpolation_centerlines"]["filepath"])
    polygons = gpd.read_file(config["interpolation_polygons"]["filepath"])

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
    survey_points = gpd.GeoDataFrame(df, geometry=geometry)


@app.command()
def calculate_eac(name: str):
    print(f"Hello {name}")


if __name__ == "__main__":
    app()
