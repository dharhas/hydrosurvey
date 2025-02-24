import datetime
import tomllib
from pathlib import Path

import panel as pn
import tomli_w

from .widgets import CommandRunner, FileFolderPicker

pn.extension("modal", "terminal")

config_mapper = {
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


def get_data_fields(cols):
    return {k: v for k, v in cols.items() if "_column" in k}


lake = pn.widgets.TextInput(
    name=config_mapper["lake"]["name"], placeholder="Enter Lake Name"
)
year = pn.widgets.IntInput(
    name=config_mapper["lake"]["survey_year"], value=datetime.date.today().year
)

# boundary
boundary_file = FileFolderPicker(
    name=config_mapper["boundary"]["filepath"],
    data_fields=get_data_fields(config_mapper["boundary"]),
    file_pattern="*.shp",
)
boundary_max_segment_length = pn.widgets.IntInput(
    name=config_mapper["boundary"]["max_segment_length"], value=10
)

# survey points
survey_points_file = FileFolderPicker(
    name=config_mapper["survey_points"]["filepath"],
    data_fields=get_data_fields(config_mapper["survey_points"]),
    file_pattern="*.csv",
)
survey_points_crs = pn.widgets.TextInput(
    name=config_mapper["survey_points"]["crs"],
    placeholder="Optional: default is boundary CRS",
)

# interpolation centerlines
interpolation_centerlines_file = FileFolderPicker(
    name=config_mapper["interpolation_centerlines"]["filepath"],
    data_fields=get_data_fields(config_mapper["interpolation_centerlines"]),
    file_pattern="*.shp",
)
centerline_max_segment_length = pn.widgets.IntInput(
    name=config_mapper["interpolation_centerlines"]["max_segment_length"], value=10
)

# interpolation polygons
interpolation_polygons_file = FileFolderPicker(
    name=config_mapper["interpolation_polygons"]["filepath"],
    data_fields=get_data_fields(config_mapper["interpolation_polygons"]),
    file_pattern="*.shp",
)
buffer = pn.widgets.IntInput(
    name=config_mapper["interpolation_polygons"]["buffer"], value=100
)
nearest_neighbors = pn.widgets.IntInput(
    name=config_mapper["interpolation_polygons"]["nearest_neighbors"], value=100
)

# output directory
output_file_dir = FileFolderPicker(
    name="Output Folder",
    only_folders=True,
)
output_file_name = pn.widgets.TextInput(name="Output File Name", value="output")

terminal = CommandRunner()
cli_command = pn.widgets.StaticText(
    name="CLI Command: ",
    value="hstools interpolate-lake /path/to/config.toml",
    # disabled=True,
)


def on_run_button_clicked(event):
    config = {}
    config["lake"] = {}
    config["lake"]["name"] = lake.value
    config["lake"]["survey_year"] = year.value

    # selected = boundary_file.get_selected()
    config["boundary"] = boundary_file.get_selected()
    config["boundary"]["max_segment_length"] = boundary_max_segment_length.value

    config["survey_points"] = survey_points_file.get_selected()
    config["survey_points"]["crs"] = survey_points_crs.value

    config["interpolation_centerlines"] = interpolation_centerlines_file.get_selected()
    config["interpolation_centerlines"][
        "max_segment_length"
    ] = centerline_max_segment_length.value

    config["interpolation_polygons"] = interpolation_polygons_file.get_selected()
    config["interpolation_polygons"]["buffer"] = buffer.value
    config["interpolation_polygons"]["nearest_neighbors"] = nearest_neighbors.value

    config["output"] = {}
    output_filepath = (
        Path(output_file_dir.get_selected()["filepath"])
        .joinpath(output_file_name.value)
        .with_suffix(".csv")
    )
    config["output"]["filepath"] = str(output_filepath)

    if config_type.active == 0:
        config_filepath = Path(load_config.selected_path.value)
    else:
        config_filepath = (
            Path(create_config_dir.selected_path.value)
            .joinpath(create_config_file_name.value)
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
    cli_command.value = " ".join(command)
    terminal.run_command(command)


save_and_run = pn.widgets.Button(
    name="Save Config and Run",
)

save_and_run.on_click(on_run_button_clicked)


def parse_config(cols):
    return {k: v for k, v in cols.items() if "_column" in k or "filepath" in k}


# load existing config from toml file
def apply_config(event):
    if not load_config.selected_path.value:
        return

    with open(load_config.selected_path.value, "rb") as f:
        config = tomllib.load(f)

    lake.value = config["lake"]["name"]
    year.value = config["lake"]["survey_year"]

    boundary_file.set_selected(parse_config(config["boundary"]))
    boundary_max_segment_length.value = config["boundary"]["max_segment_length"]

    survey_points_file.set_selected(parse_config(config["survey_points"]))
    survey_points_crs.value = config["survey_points"].get("crs", "")

    interpolation_centerlines_file.set_selected(
        parse_config(config["interpolation_centerlines"])
    )
    centerline_max_segment_length.value = config["interpolation_centerlines"][
        "max_segment_length"
    ]

    interpolation_polygons_file.set_selected(
        parse_config(config["interpolation_polygons"])
    )
    buffer.value = config["interpolation_polygons"]["buffer"]
    nearest_neighbors.value = config["interpolation_polygons"]["nearest_neighbors"]

    output_file_dir.selected_path.value = str(Path(config["output"]["filepath"]).parent)
    output_file_name.value = Path(config["output"]["filepath"]).stem


load_config = FileFolderPicker(
    name="Existing Config File (*.toml)",
    file_pattern="*.toml",
)
# load_config_button = pn.widgets.Button(name="Load Config")
# load_config_button.on_click(apply_config)
bound_load_config = pn.bind(apply_config, load_config.selected_path)

# create config file
create_config_dir = FileFolderPicker(
    name="Config File Directory",
    only_folders=True,
)
create_config_file_name = pn.widgets.TextInput(
    name="New Config File Name (*.toml)", value="config"
)

config_type = pn.Tabs(
    pn.Column(
        load_config,
        bound_load_config,
        name="Load Existing Configuration",
    ),
    pn.Column(
        create_config_dir,
        create_config_file_name,
        name="Create New Configuration",
    ),
)

layout = pn.Row(
    pn.Spacer(width=50),
    pn.Column(
        # "## Config File",
        config_type,
        pn.layout.Divider(),
        # "## Survey Information",
        lake,
        year,
        pn.layout.Divider(),
        # "## Lake Boundary Information",
        boundary_file,
        boundary_max_segment_length,
        pn.layout.Divider(),
        # "## Survey Points Information",
        survey_points_file,
        survey_points_crs,
        pn.layout.Divider(),
        # "## Interpolation Centerlines Information",
        interpolation_centerlines_file,
        centerline_max_segment_length,
        pn.layout.Divider(),
        # "## Interpolation Polygons Information",
        interpolation_polygons_file,
        buffer,
        nearest_neighbors,
        pn.layout.Divider(),
        # "## Output Information",
        output_file_dir,
        output_file_name,
    ),
    pn.Spacer(width=100),
    pn.Column(
        # "## Interpolate Lake",
        save_and_run,
        cli_command,
        terminal,
    ),
)

# Define the main content
main_content = pn.Column()
main_content.append(layout)


# Define a function to update the main content
def update_content(event):
    if event.obj.name == "Lake Interpolation":
        main_content[0] = layout
    else:
        main_content[0] = pn.pane.Markdown(f"# {event.obj.name} is not available")


# Create the sidebar buttons
menu_lake = pn.widgets.Button(name="Lake Interpolation")
menu_eac = pn.widgets.Button(name="Elevation Area Capacity Curve")

# Attach the update function
menu_lake.on_click(update_content)
menu_eac.on_click(update_content)

# Build the sidebar
sidebar = pn.Column(
    "## Application Menu",
    # pn.layout.Divider(),
    menu_lake,
    menu_eac,
    width=25,
)

# Build the template
template = pn.template.MaterialTemplate(
    title="HydroSurvey Tools (HSTools)",
    sidebar=sidebar,
    main=[main_content],
)
