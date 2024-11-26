import datetime
from pathlib import Path

import click
import hydrofunctions as hf
import pandas as pd
import sdi


@click.command()
@click.argument("path", type=click.Path(exists=True, resolve_path=True))
@click.argument("tide_file", type=click.Path(exists=True, resolve_path=True))
@click.argument("output_file", type=click.Path(resolve_path=True))
# @click.argument("usgs_site", type=str)
@click.argument("usgs_parameter", type=str)
def main(path, tide_file, output_file, usgs_parameter):  # usgs_site, usgs_parameter):
    """Simple program that greets NAME for a total of COUNT times."""
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


if __name__ == "__main__":
    main()
