import datetime
import tomllib
from pathlib import Path

import panel as pn
import tomli_w

from .widgets import CommandRunner, EACViewer, FileFolderPicker, InterpolateLakeViewer, SDI2CSVViewer

pn.extension("modal", "terminal")


# Define a function to update the main content
def update_content(event):
    if event.obj.name == "Lake Interpolation":
        main_content[0] = lake_viewer
    elif event.obj.name == "Elevation Area Capacity Curve":
        main_content[0] = eac_viewer
    elif event.obj.name == "SDI to CSV":
        main_content[0] = sdi2csv_viewer
    else:
        main_content[0] = pn.pane.Markdown(f"# {event.obj.name} is not available")


lake_viewer = InterpolateLakeViewer()
eac_viewer = EACViewer()
sdi2csv_viewer = SDI2CSVViewer()

# Define the main content
main_content = pn.Column(lake_viewer)

# Create the sidebar buttons
menu_lake = pn.widgets.Button(name="Lake Interpolation")
menu_eac = pn.widgets.Button(name="Elevation Area Capacity Curve")
menu_sdi2csv = pn.widgets.Button(name="SDI to CSV")

# Attach the update function
menu_lake.on_click(update_content)
menu_eac.on_click(update_content)
menu_sdi2csv.on_click(update_content)

# Build the sidebar
sidebar = pn.Column(
    "## Application Menu",
    # pn.layout.Divider(),
    menu_lake,
    menu_eac,
    menu_sdi2csv,
    width=25,
)

# Build the template
template = pn.template.MaterialTemplate(
    title="HydroSurvey Tools (HSTools)",
    sidebar=sidebar,
    main=[main_content],
)
