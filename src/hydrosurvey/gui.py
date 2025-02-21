import panel as pn
from widgets import ColumnMapper, FileSelectorModal

pn.extension("terminal")
# pn.config.theme = "dark"


def run(event):

    term.clear()
    term.subprocess.run(
        "hstools",
        "interpolate-lake",
        "/Users/dharhas/data/bianca_20241118/RedBluff_config1.toml",
        # shell=True,
        # stdout=term,
    )


lake = pn.widgets.TextInput(name="Lake", placeholder="Enter Lake Name")
year = pn.widgets.IntInput(
    name="Survey Year", value=2025, placeholder="Enter Survey Year"
)

# boundary
boundary_file = ColumnMapper(
    name="Lake Boundary ShapeFile",
    data_fields=["elevation"],
    FileSelectorParams={"directory": "~/", "file_pattern": "*.shp"},
)
boundary_max_segment_length = pn.widgets.IntInput(name="Max Segment Length", value=10)
boundary_crs = pn.widgets.TextInput(name="CRS", disabled=True)

# survey points
survey_points_file = ColumnMapper(
    name="Survey Points CSV",
    data_fields=["x_coord", "y_coord", "surface_elevation", "preimpoundment_elevation"],
    FileSelectorParams={"directory": "~/", "file_pattern": "*.csv"},
)

# interpolation centerlines
interpolation_centerlines_file = ColumnMapper(
    name="Interpolation Centerlines ShapeFile",
    data_fields=["polygon id"],
    FileSelectorParams={"directory": "~/", "file_pattern": "*.shp"},
)
centerline_max_segment_length = pn.widgets.IntInput(name="Max Segment Length", value=10)


# interpolation polygons
interpolation_polygons_file = ColumnMapper(
    name="Interpolation Polygons ShapeFile",
    data_fields=["polygon id", "grid spacing", "priority", "method", "params"],
    FileSelectorParams={"directory": "~/", "file_pattern": "*.shp"},
)
buffer = pn.widgets.IntInput(name="Buffer", value=100)
nearest_neighbors = pn.widgets.IntInput(name="Nearest Neighbors", value=100)

# output directory
output_file = FileSelectorModal(
    name="Output Directory",
    FileSelectorParams={"directory": "~/", "file_pattern": ""},
)
output_file_name = pn.widgets.TextInput(name="Output File Name", value="output")


# Instantiate the template with widgets displayed in the sidebar
template = pn.template.MaterialTemplate(
    title="HydroSurvey Tools (HSTools)",
)

term = pn.widgets.Terminal("HSTools Execution \n\n")
save_and_run = pn.widgets.Button(name="Save and Run", button_type="primary")

save_and_run.on_click(
    run
)  # lambda event: term.subprocess.run("hstools", "interpolate-lake", "config.toml"))
kill = pn.widgets.Button(name="Kill Python", button_type="danger")
kill.on_click(lambda x: term.subprocess.kill())

tn = pn.Column(
    pn.Row(save_and_run, kill, term.subprocess.param.running),
    term,
    sizing_mode="stretch_both",
    min_height=500,
)

# add button to load config from toml file
load_config = FileSelectorModal(
    name="Load Existing Configuration (*.toml)",
    FileSelectorParams={"directory": "~/", "file_pattern": "*.toml"},
)

# create config file
create_config = FileSelectorModal(
    name="Create New Configuration (*.toml)",
    FileSelectorParams={"directory": "~/", "file_pattern": ""},
)
config_file_name = pn.widgets.TextInput(name="Config File Name", value="config.toml")

layout = pn.Row(
    pn.Column(
        pn.Card(
            pn.Tabs(
                pn.Column(
                    load_config,
                    name="Load Existing Configuration",
                ),
                pn.Column(
                    create_config,
                    config_file_name,
                    name="Create New Configuration",
                ),
            ),
            title="Configuration File",
        ),
        pn.Card(lake, year, title="Survey Information"),
        pn.Card(
            boundary_file,
            boundary_max_segment_length,
            title="Lake Boundary Information",
        ),
        pn.Card(survey_points_file, title="Survey Points Information"),
        pn.Card(
            interpolation_centerlines_file,
            centerline_max_segment_length,
            title="Interpolation Centerlines Information",
        ),
        pn.Card(
            interpolation_polygons_file,
            buffer,
            nearest_neighbors,
            title="Interpolation Polygons Information",
        ),
        pn.Card(
            output_file,
            output_file_name,
            title="Output Information",
        ),
    ),
    tn,
)

layout.servable()

# template.main.append(layout)
# template.servable()
