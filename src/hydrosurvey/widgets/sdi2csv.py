from pathlib import Path

import panel as pn
from panel.viewable import Viewer

from .command_runner import CommandRunner
from .file_picker import FileFolderPicker


class SDI2CSVViewer(Viewer):
    def __init__(self, **params):
        self.command_runner = CommandRunner()
        self.sdi_folder = FileFolderPicker(
            name="SDI Files Folder",
            only_folders=True,
        )
        self.apply_tide_corrections = pn.widgets.Checkbox(
            name="Apply Tide Corrections",
            value=False,
        )
        self.tide_file = FileFolderPicker(
            name="Tide File (USGS RDB format)",
            only_folders=False,
        )
        self.usgs_parameter = pn.widgets.TextInput(
            name="USGS Parameter",
            value="",
            placeholder="Enter USGS parameter code",
        )

        # Create a column for tide-related widgets
        self.tide_widgets = pn.Column(
            self.tide_file,
            self.usgs_parameter,
            visible=False,
        )

        # Watch the checkbox to show/hide tide widgets
        self.apply_tide_corrections.param.watch(
            self._toggle_tide_widgets, "value"
        )

        self.cli_command = pn.widgets.StaticText(
            name="CLI Command: ",
            value="hstools sdi2csv /path/to/sdi/folder /path/to/output.csv",
        )

        self.run_button = pn.widgets.Button(name="Run SDI2CSV")
        self.run_button.on_click(self.run_sdi2csv)

        # output directory
        self.output_file_dir = FileFolderPicker(
            name="Output Folder",
            only_folders=True,
        )
        self.output_file_name = pn.widgets.TextInput(
            name="Output File Name", value="output"
        )

        self.layout = pn.Column(
            pn.pane.Markdown("# Convert SDI to CSV"),
            pn.layout.Divider(),
            pn.Row(
                pn.Column(
                    self.sdi_folder,
                    self.apply_tide_corrections,
                    self.tide_widgets,
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

    def _toggle_tide_widgets(self, event):
        """Toggle visibility of tide-related widgets based on checkbox state."""
        self.tide_widgets.visible = event.new

    def run_sdi2csv(self, event):
        command = [
            "hstools",
            "sdi2csv",
            self.sdi_folder.get_selected()["filepath"],
            str(
                Path(self.output_file_dir.get_selected()["filepath"])
                .joinpath(self.output_file_name.value)
                .with_suffix(".csv")
            ),
        ]

        # Add tide correction parameters if checkbox is checked
        if self.apply_tide_corrections.value:
            command.extend([
                "--tide-file",
                self.tide_file.get_selected()["filepath"],
                "--usgs-parameter",
                self.usgs_parameter.value,
            ])

        self.cli_command.value = " ".join(command)
        self.command_runner.run_command(command)

    def __panel__(self):
        return self.layout