import panel as pn
from widgets import ColumnMapper, FileSelectorModal

# pn.config.theme = "dark"

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


layout = pn.Column(
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
    ),
)
# .servable()

template.main.append(layout)
template.servable()
# Append a layout to the main area, to demonstrate the list-like API
# template.main.append(
#     pn.Column(
#         pn.Card(lake, year, title="Survey Information"),
#         pn.Card(
#             boundary_file,
#             boundary_max_segment_length,
#             title="Lake Boundary Information",
#         ),
#         pn.Card(survey_points_file, title="Survey Points Information"),
#         pn.Card(
#             interpolation_centerlines_file,
#             centerline_max_segment_length,
#             title="Interpolation Centerlines Information",
#         ),
#         pn.Card(
#             interpolation_polygons_file,
#             buffer,
#             nearest_neighbors,
#             title="Interpolation Polygons Information",
#         ),
#         pn.Card(
#             output_file,
#             output_file_name,
#         ),
#     )
# )

# template.servable()
