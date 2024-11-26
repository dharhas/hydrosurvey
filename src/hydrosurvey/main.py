import tomllib
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import typer
from rich import print
from shapely.geometry import Point

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
    aeidw(config)


@app.command()
def calculate_eac(name: str):
    print(f"Hello {name}")


if __name__ == "__main__":
    app()
