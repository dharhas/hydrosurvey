import tomllib
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import typer
from rich import print

from .interpolate import aeidw

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
    interpolated_points = aeidw(config)

    # write out the interpolated elevations
    print(f"Writing interpolated elevations to {config['output']['filepath']}")
    points_to_csv(interpolated_points, config["output"]["filepath"])


@app.command()
def calculate_eac(name: str):
    print(f"Hello {name}")


def points_to_csv(gdf: gpd.GeoDataFrame, output_file: str):
    # Extract coordinates
    gdf["x_coordinate"] = gdf.geometry.x
    gdf["y_coordinate"] = gdf.geometry.y

    # Drop the geometry column
    gdf = gdf.drop(columns="geometry")

    # Write to CSV
    print(f"Writing DataFrame to {output_file}")
    gdf.to_csv(output_file, index=False)


if __name__ == "__main__":
    app()
