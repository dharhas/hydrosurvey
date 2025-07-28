from pathlib import Path

import panel as pn
from panel.viewable import Viewer

from .command_runner import CommandRunner
from .file_picker import FileFolderPicker


class WriteXYZViewer(Viewer):
    def __init__(self, **params):
        self.command_runner = CommandRunner()
        self.sdi_folder = FileFolderPicker(
            name="SDI Files Folder",
            only_folders=True,
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

        self.cli_command = pn.widgets.StaticText(
            name="CLI Command: ",
            value="hstools write-xyz /path/to/sdi/folder /path/to/tide.rdb /path/to/output.csv <usgs_parameter>",
        )

        self.run_button = pn.widgets.Button(name="Run Write XYZ")
        self.run_button.on_click(self.run_write_xyz)

        # output directory
        self.output_file_dir = FileFolderPicker(
            name="Output Folder",
            only_folders=True,
        )
        self.output_file_name = pn.widgets.TextInput(
            name="Output File Name", value="output"
        )

        self.layout = pn.Column(
            pn.pane.Markdown("# Write XYZ from SDI Files"),
            pn.layout.Divider(),
            pn.Row(
                pn.Column(
                    self.sdi_folder,
                    self.tide_file,
                    self.usgs_parameter,
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

    def run_write_xyz(self, event):
        command = [
            "hstools",
            "write-xyz",
            self.sdi_folder.get_selected()["filepath"],
            self.tide_file.get_selected()["filepath"],
            str(
                Path(self.output_file_dir.get_selected()["filepath"])
                .joinpath(self.output_file_name.value)
                .with_suffix(".csv")
            ),
            self.usgs_parameter.value,
        ]

        self.cli_command.value = " ".join(command)
        self.command_runner.run_command(command)

    def __panel__(self):
        return self.layout