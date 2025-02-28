from pathlib import Path

import panel as pn
from panel.viewable import Viewer

from .command_runner import CommandRunner
from .file_picker import FileFolderPicker


class EACViewer(Viewer):
    def __init__(self, **params):
        self.command_runner = CommandRunner()
        self.dem = FileFolderPicker()
        self.lake_boundary_elevation = pn.widgets.FloatInput(
            name="Lake Boundary Elevation",
            value=None,
            placeholder="Optional: Default is max DEM elevation",
        )
        self.step_size = pn.widgets.FloatInput(
            name="Elevation Step Size",
            value=1.0,
            placeholder="Optional: Default is 1.0",
        )
        self.no_data = pn.widgets.FloatInput(
            name="Override DEM No Data Value",
            value=None,
            placeholder="Optional: Default is from DEM",
        )
        self.plot_eac_curve = pn.widgets.Checkbox(
            name="Generate Elevation Area Capacity Plot", value=False
        )

        self.cli_command = pn.widgets.StaticText(
            name="CLI Command: ",
            value="hstools compute-eac /path/to/dem.tiff /path/to/output.csv",
        )

        self.run_button = pn.widgets.Button(name="Run EAC")
        self.run_button.on_click(self.run_eac)

        # output directory
        self.output_file_dir = FileFolderPicker(
            name="Output Folder",
            only_folders=True,
        )
        self.output_file_name = pn.widgets.TextInput(
            name="Output File Name", value="output"
        )

        self.layout = pn.Column(
            pn.pane.Markdown("# Compute Elevation Area Capacity"),
            pn.layout.Divider(),
            pn.Row(
                pn.Column(
                    self.dem,
                    self.lake_boundary_elevation,
                    self.step_size,
                    self.no_data,
                    self.plot_eac_curve,
                    self.output_file_dir,
                    self.output_file_name,
                ),
                pn.Column(
                    self.cli_command,
                    self.run_button,
                    self.command_runner,
                ),
            ),
        )

    def run_eac(self, event):
        command = [
            "hstools",
            "compute-eac",
            self.dem.get_selected()["filepath"],
            str(
                Path(self.output_file_dir.get_selected()["filepath"])
                .joinpath(self.output_file_name.value)
                .with_suffix(".csv")
            ),
        ]
        if self.lake_boundary_elevation.value:
            command.extend(
                ["--lake-elevation", str(self.lake_boundary_elevation.value)]
            )

        if self.step_size.value:
            command.extend(["--step-size", str(self.step_size.value)])

        if self.no_data.value:
            command.extend(["--override-nodata", str(self.no_data.value)])

        if self.plot_eac_curve.value:
            command.append("--plot-curve")

        self.cli_command.value = " ".join(command)
        self.command_runner.run_command(command)

    def __panel__(self):
        return self.layout
