import datetime
import logging
import sys
import tomllib
from pathlib import Path

import panel as pn
import tomli_w

from . import CommandRunner, FileFolderPicker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

pn.extension("modal", "terminal")


class InterpolateLakeViewer(pn.viewable.Viewer):
    def __init__(self, **params):
        super().__init__(**params)

        self.config_mapper = {
            "lake": {
                "name": "Lake",
                "survey_year": "Survey Year",
            },
            "boundary": {
                "filepath": "Boundary ShapeFile",
                "elevation_column": "Elevation",
                "max_segment_length": "Max Segment Length",
            },
            "survey_points": {
                "filepath": "Survey Points (*.csv)",
                "x_coord_column": "X Coordinate",
                "y_coord_column": "Y Coordinate",
                "current_surface_elevation_column": "Surface Elevation",
                "preimpoundment_elevation_column": "Pre-Impoundment Elevation",
                "crs": "Survey Points CRS",
            },
            "interpolation_centerlines": {
                "filepath": "Interpolation Centerlines ShapeFile",
                "polygon_id_column": "Polygon Id",
                "max_segment_length": "Max Segment Length",
            },
            "interpolation_polygons": {
                "filepath": "Interpolation Polygons ShapeFile",
                "polygon_id_column": "Polygon Id",
                "grid_spacing_column": "Grid Spacing",
                "priority_column": "Polygin Priority",
                "interpolation_method_column": "Interpolation Method",
                "interpolation_params_column": "Interpolation Parameters",
                "buffer": "Polygon Buffer",
                "nearest_neighbors": "Nearest Neighbors",
            },
            "output": {
                "filepath": "Output File",
            },
        }

        self.lake = pn.widgets.TextInput(
            name=self.config_mapper["lake"]["name"], placeholder="Enter Lake Name"
        )
        self.year = pn.widgets.IntInput(
            name=self.config_mapper["lake"]["survey_year"],
            value=datetime.date.today().year,
        )

        # boundary
        self.boundary_file = FileFolderPicker(
            name=self.config_mapper["boundary"]["filepath"],
            data_fields=self.get_data_fields(self.config_mapper["boundary"]),
            file_pattern="*.shp",
        )
        self.boundary_max_segment_length = pn.widgets.IntInput(
            name=self.config_mapper["boundary"]["max_segment_length"], value=10
        )

        # survey points
        self.survey_points_file = FileFolderPicker(
            name=self.config_mapper["survey_points"]["filepath"],
            data_fields=self.get_data_fields(self.config_mapper["survey_points"]),
            file_pattern="*.csv",
        )
        self.survey_points_crs = pn.widgets.TextInput(
            name=self.config_mapper["survey_points"]["crs"],
            placeholder="Optional: default is boundary CRS",
        )

        # interpolation centerlines
        self.interpolation_centerlines_file = FileFolderPicker(
            name=self.config_mapper["interpolation_centerlines"]["filepath"],
            data_fields=self.get_data_fields(
                self.config_mapper["interpolation_centerlines"]
            ),
            file_pattern="*.shp",
        )
        self.centerline_max_segment_length = pn.widgets.IntInput(
            name=self.config_mapper["interpolation_centerlines"]["max_segment_length"],
            value=10,
        )

        # interpolation polygons
        self.interpolation_polygons_file = FileFolderPicker(
            name=self.config_mapper["interpolation_polygons"]["filepath"],
            data_fields=self.get_data_fields(
                self.config_mapper["interpolation_polygons"]
            ),
            file_pattern="*.shp",
        )
        self.buffer = pn.widgets.IntInput(
            name=self.config_mapper["interpolation_polygons"]["buffer"], value=100
        )
        self.nearest_neighbors = pn.widgets.IntInput(
            name=self.config_mapper["interpolation_polygons"]["nearest_neighbors"],
            value=100,
        )

        # output directory
        self.output_file_dir = FileFolderPicker(
            name="Output Folder",
            only_folders=True,
        )
        self.output_file_name = pn.widgets.TextInput(
            name="Output File Name", value="output"
        )

        self.terminal = CommandRunner()
        self.cli_command = pn.widgets.StaticText(
            name="CLI Command: ",
            value="hstools interpolate-lake /path/to/config.toml",
            # disabled=True,
        )

        self.save_and_run = pn.widgets.Button(
            name="Save Config and Run",
        )
        self.save_and_run.on_click(self.on_run_button_clicked)

        # load existing config from toml file
        self.load_config = FileFolderPicker(
            name="Existing Config File (*.toml)",
            file_pattern="*.toml",
        )
        self.bound_load_config = pn.bind(
            self.apply_config, self.load_config.selected_path
        )

        # create config file
        self.create_config_dir = FileFolderPicker(
            name="Config File Directory",
            only_folders=True,
        )
        self.create_config_file_name = pn.widgets.TextInput(
            name="New Config File Name (*.toml)", value="config"
        )

        self.config_type = pn.Tabs(
            pn.Column(
                self.load_config,
                self.bound_load_config,
                name="Load Existing Configuration",
            ),
            pn.Column(
                self.create_config_dir,
                self.create_config_file_name,
                name="Create New Configuration",
            ),
        )

        self.layout = pn.Row(
            pn.Spacer(width=50),
            pn.Column(
                # "## Config File",
                self.config_type,
                pn.layout.Divider(),
                # "## Survey Information",
                self.lake,
                self.year,
                pn.layout.Divider(),
                # "## Lake Boundary Information",
                self.boundary_file,
                self.boundary_max_segment_length,
                pn.layout.Divider(),
                # "## Survey Points Information",
                self.survey_points_file,
                self.survey_points_crs,
                pn.layout.Divider(),
                # "## Interpolation Centerlines Information",
                self.interpolation_centerlines_file,
                self.centerline_max_segment_length,
                pn.layout.Divider(),
                # "## Interpolation Polygons Information",
                self.interpolation_polygons_file,
                self.buffer,
                self.nearest_neighbors,
                pn.layout.Divider(),
                # "## Output Information",
                self.output_file_dir,
                self.output_file_name,
            ),
            pn.Spacer(width=100),
            pn.Column(
                # "## Interpolate Lake",
                self.save_and_run,
                self.cli_command,
                self.terminal,
            ),
        )

    def __panel__(self):
        return self.layout

    def get_data_fields(self, cols):
        return {k: v for k, v in cols.items() if "_column" in k}

    def on_run_button_clicked(self, event):
        config = {}
        config["lake"] = {}
        config["lake"]["name"] = self.lake.value
        config["lake"]["survey_year"] = self.year.value

        # selected = boundary_file.get_selected()
        config["boundary"] = self.boundary_file.get_selected()
        config["boundary"][
            "max_segment_length"
        ] = self.boundary_max_segment_length.value

        config["survey_points"] = self.survey_points_file.get_selected()
        config["survey_points"]["crs"] = self.survey_points_crs.value

        config["interpolation_centerlines"] = (
            self.interpolation_centerlines_file.get_selected()
        )
        config["interpolation_centerlines"][
            "max_segment_length"
        ] = self.centerline_max_segment_length.value

        config["interpolation_polygons"] = (
            self.interpolation_polygons_file.get_selected()
        )
        config["interpolation_polygons"]["buffer"] = self.buffer.value
        config["interpolation_polygons"][
            "nearest_neighbors"
        ] = self.nearest_neighbors.value

        config["output"] = {}
        output_filepath = (
            Path(self.output_file_dir.get_selected()["filepath"])
            .joinpath(self.output_file_name.value)
            .with_suffix(".csv")
        )
        config["output"]["filepath"] = str(output_filepath)

        if self.config_type.active == 0:
            config_filepath = Path(self.load_config.selected_path.value)
        else:
            config_filepath = (
                Path(self.create_config_dir.selected_path.value)
                .joinpath(self.create_config_file_name.value)
                .with_suffix(".toml")
            )

        # toml can't handle None values
        def replace_none(d):
            """Recursively replace None values with an empty string in a nested dictionary."""
            if isinstance(d, dict):
                return {k: replace_none(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [replace_none(v) for v in d]
            return "" if d is None else d

        with open(config_filepath, "wb") as f:
            tomli_w.dump(replace_none(config), f)

        command = [
            "hstools",
            "interpolate-lake",
            str(config_filepath),
        ]
        self.cli_command.value = " ".join(command)
        self.terminal.run_command(command)

    def parse_config(self, cols):
        return {k: v for k, v in cols.items() if "_column" in k or "filepath" in k}

    # load existing config from toml file
    def apply_config(self, event):
        if not self.load_config.selected_path.value:
            return

        with open(self.load_config.selected_path.value, "rb") as f:
            config = tomllib.load(f)

        self.lake.value = config["lake"]["name"]
        self.year.value = config["lake"]["survey_year"]

        self.boundary_file.set_selected(self.parse_config(config["boundary"]))
        self.boundary_max_segment_length.value = config["boundary"][
            "max_segment_length"
        ]

        self.survey_points_file.set_selected(self.parse_config(config["survey_points"]))
        self.survey_points_crs.value = config["survey_points"].get("crs", "")

        self.interpolation_centerlines_file.set_selected(
            self.parse_config(config["interpolation_centerlines"])
        )
        self.centerline_max_segment_length.value = config["interpolation_centerlines"][
            "max_segment_length"
        ]

        self.interpolation_polygons_file.set_selected(
            self.parse_config(config["interpolation_polygons"])
        )
        self.buffer.value = config["interpolation_polygons"]["buffer"]
        self.nearest_neighbors.value = config["interpolation_polygons"][
            "nearest_neighbors"
        ]

        self.output_file_dir.selected_path.value = str(
            Path(config["output"]["filepath"]).parent
        )
        self.output_file_name.value = Path(config["output"]["filepath"]).stem
