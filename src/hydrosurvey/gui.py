import tomllib
from pathlib import Path

import panel as pn
import tomli_w
from widgets import ColumnMapper, CommandRunner, FileSelectorModal

pn.extension("modal", "terminal")

lake = pn.widgets.TextInput(name="Lake", placeholder="Enter Lake Name")
year = pn.widgets.IntInput(
    name="Survey Year", value=2025, placeholder="Enter Survey Year"
)


input_dir = "~/"
# boundary
boundary_file = ColumnMapper(
    name="Lake Boundary ShapeFile",
    data_fields=["elevation"],
    FileSelectorParams={"directory": input_dir, "file_pattern": "*.shp"},
)
boundary_max_segment_length = pn.widgets.IntInput(name="Max Segment Length", value=10)
boundary_crs = pn.widgets.TextInput(name="CRS", disabled=True)

# survey points
survey_points_file = ColumnMapper(
    name="Survey Points CSV",
    data_fields=["x_coord", "y_coord", "surface_elevation", "preimpoundment_elevation"],
    FileSelectorParams={"directory": input_dir, "file_pattern": "*.csv"},
)
survey_points_crs = pn.widgets.TextInput(name="Survey Points CRS")

# interpolation centerlines
interpolation_centerlines_file = ColumnMapper(
    name="Interpolation Centerlines ShapeFile",
    data_fields=["polygon id"],
    FileSelectorParams={"directory": input_dir, "file_pattern": "*.shp"},
)
centerline_max_segment_length = pn.widgets.IntInput(name="Max Segment Length", value=10)


# interpolation polygons
interpolation_polygons_file = ColumnMapper(
    name="Interpolation Polygons ShapeFile",
    data_fields=["polygon id", "grid spacing", "priority", "method", "params"],
    FileSelectorParams={"directory": input_dir, "file_pattern": "*.shp"},
)
buffer = pn.widgets.IntInput(name="Buffer", value=100)
nearest_neighbors = pn.widgets.IntInput(name="Nearest Neighbors", value=100)

# output directory
output_file_dir = FileSelectorModal(
    name="Output Directory",
    FileSelectorParams={"directory": "~/", "file_pattern": ""},
)
output_file_name = pn.widgets.TextInput(name="Output File Name", value="output")

terminal = CommandRunner()
cli_command = pn.widgets.TextInput(
    name="CLI Command",
    value="hstools interpolate-lake /path/to/config.toml",
    disabled=True,
)


def on_run_button_clicked(event):
    config = {}
    config["lake"] = {}
    config["lake"]["name"] = lake.value
    config["lake"]["survey_year"] = year.value

    config["boundary"] = {}
    config["boundary"]["filepath"] = boundary_file.input_file.selected_file.value
    config["boundary"]["elevation_column"] = boundary_file.mapping_widgets[
        "elevation"
    ].value
    config["boundary"]["max_segment_length"] = boundary_max_segment_length.value

    config["survey_points"] = {}
    config["survey_points"][
        "filepath"
    ] = survey_points_file.input_file.selected_file.value
    config["survey_points"]["x_coord_column"] = survey_points_file.mapping_widgets[
        "x_coord"
    ].value
    config["survey_points"]["y_coord_column"] = survey_points_file.mapping_widgets[
        "y_coord"
    ].value
    config["survey_points"]["surface_elevation_column"] = (
        survey_points_file.mapping_widgets["surface_elevation"].value
    )
    config["survey_points"]["preimpoundment_elevation_column"] = (
        survey_points_file.mapping_widgets["preimpoundment_elevation"].value
    )
    config["survey_points"]["crs"] = survey_points_crs.value
    if config["survey_points"]["crs"] == "":
        config["survey_points"]["crs"] = boundary_crs.value

    config["interpolation_centerlines"] = {}
    config["interpolation_centerlines"][
        "filepath"
    ] = interpolation_centerlines_file.input_file.selected_file.value
    config["interpolation_centerlines"]["polygon_id_column"] = (
        interpolation_centerlines_file.mapping_widgets["polygon id"].value
    )
    config["interpolation_centerlines"][
        "max_segment_length"
    ] = centerline_max_segment_length.value

    config["interpolation_polygons"] = {}
    config["interpolation_polygons"][
        "filepath"
    ] = interpolation_polygons_file.input_file.selected_file.value
    config["interpolation_polygons"]["polygon_id_column"] = (
        interpolation_polygons_file.mapping_widgets["polygon id"].value
    )
    config["interpolation_polygons"]["grid_spacing_column"] = (
        interpolation_polygons_file.mapping_widgets["grid spacing"].value
    )
    config["interpolation_polygons"]["priority_column"] = (
        interpolation_polygons_file.mapping_widgets["priority"].value
    )
    config["interpolation_polygons"]["interpolation_method_column"] = (
        interpolation_polygons_file.mapping_widgets["method"].value
    )
    config["interpolation_polygons"]["interpolation_params_column"] = (
        interpolation_polygons_file.mapping_widgets["params"].value
    )
    config["interpolation_polygons"]["buffer"] = buffer.value
    config["interpolation_polygons"]["nearest_neighbors"] = nearest_neighbors.value

    config["output"] = {}
    output_filepath = (
        Path(output_file_dir.selected_file.value)
        .joinpath(output_file_name.value)
        .with_suffix(".csv")
    )
    config["output"]["filepath"] = str(output_filepath)

    if config_type.active == 0:
        config_filepath = Path(load_config.selected_file.value)
    else:
        config_filepath = (
            Path(create_config_dir.selected_file.value)
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


# load existing config from toml file
def apply_config(event):
    if not load_config.selected_file.value:
        return

    with open(load_config.selected_file.value, "rb") as f:
        config = tomllib.load(f)

    lake.value = config["lake"]["name"]
    year.value = config["lake"]["survey_year"]

    boundary_file.input_file.selected_file.value = config["boundary"]["filepath"]
    boundary_file.mapping_widgets["elevation"].value = config["boundary"][
        "elevation_column"
    ]
    boundary_max_segment_length.value = config["boundary"]["max_segment_length"]

    survey_points_file.input_file.selected_file.value = config["survey_points"][
        "filepath"
    ]
    survey_points_file.mapping_widgets["x_coord"].value = config["survey_points"][
        "x_coord_column"
    ]
    survey_points_file.mapping_widgets["y_coord"].value = config["survey_points"][
        "y_coord_column"
    ]
    survey_points_file.mapping_widgets["surface_elevation"].value = config[
        "survey_points"
    ]["surface_elevation_column"]
    survey_points_file.mapping_widgets["preimpoundment_elevation"].value = config[
        "survey_points"
    ]["preimpoundment_elevation_column"]
    survey_points_crs.value = config["survey_points"]["crs"]

    interpolation_centerlines_file.input_file.selected_file.value = config[
        "interpolation_centerlines"
    ]["filepath"]
    interpolation_centerlines_file.mapping_widgets["polygon id"].value = config[
        "interpolation_centerlines"
    ]["polygon_id_column"]
    centerline_max_segment_length.value = config["interpolation_centerlines"][
        "max_segment_length"
    ]

    interpolation_polygons_file.input_file.selected_file.value = config[
        "interpolation_polygons"
    ]["filepath"]
    interpolation_polygons_file.mapping_widgets["polygon id"].value = config[
        "interpolation_polygons"
    ]["polygon_id_column"]
    interpolation_polygons_file.mapping_widgets["grid spacing"].value = config[
        "interpolation_polygons"
    ]["grid_spacing_column"]
    interpolation_polygons_file.mapping_widgets["priority"].value = config[
        "interpolation_polygons"
    ]["priority_column"]
    interpolation_polygons_file.mapping_widgets["method"].value = config[
        "interpolation_polygons"
    ]["interpolation_method_column"]
    interpolation_polygons_file.mapping_widgets["params"].value = config[
        "interpolation_polygons"
    ]["interpolation_params_column"]
    buffer.value = config["interpolation_polygons"]["buffer"]
    nearest_neighbors.value = config["interpolation_polygons"]["nearest_neighbors"]

    output_file_dir.selected_file.value = str(Path(config["output"]["filepath"]).parent)
    output_file_name.value = Path(config["output"]["filepath"]).stem


load_config = FileSelectorModal(
    name="Existing Config File (*.toml)",
    FileSelectorParams={"directory": "~/", "file_pattern": "*.toml"},
)
bound_load_config = pn.bind(apply_config, load_config.selected_file)

# create config file
create_config_dir = FileSelectorModal(
    name="Config File Directory",
    FileSelectorParams={"directory": "~/", "file_pattern": ""},
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

template.servable()
