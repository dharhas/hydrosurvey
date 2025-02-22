import subprocess
import threading
from pathlib import Path, WindowsPath

import geopandas as gpd
import pandas as pd
import panel as pn
import psutil
from panel.viewable import Viewer

pn.extension("modal")


class FileSelectorModal(Viewer):
    def __init__(
        self, FileSelectorParams={}, name="Selected File", default_file="", **params
    ):

        super().__init__(**params)

        # Create the FileSelector widget
        self.file_selector = pn.widgets.FileSelector(
            **FileSelectorParams,
        )

        # Create buttons
        # self.open_modal_button = pn.widgets.Button(name="Select", button_type="primary")
        self.open_modal_button = pn.widgets.ButtonIcon(
            icon="folder-open",
            size="2em",
        )
        self.close_modal_button = pn.widgets.Button(name="Close", align="end")

        # Create a TextInput widget to display the selected file
        self.selected_file = pn.widgets.TextInput(
            name=name,
            disabled=True,
            value=default_file,
        )

        # Create the modal content
        self.modal_content = pn.Column(
            self.file_selector,
            self.close_modal_button,
        )

        # Attach the button callbacks
        self.open_modal_button.on_click(self.open_modal)
        self.close_modal_button.on_click(self.close_modal)

        # Create the layout
        self.layout = pn.Row(
            self.selected_file,
            self.open_modal_button,
        )

    def open_modal(self, event):
        self.modal = pn.Modal(self.modal_content)

        # Add a param watcher to detect when the modal is closed
        self.modal.param.watch(self.modal_open_did_change, "open")
        self.layout.append(self.modal)
        self.modal.open = True

    def close_modal(self, event):
        self.modal.open = False

    def modal_open_did_change(self, event):
        if self.modal.open == False:
            if self.file_selector.value:
                self.selected_file.value = self.file_selector.value[0]
            self.layout.remove(self.modal)
            self.modal = None

    def __panel__(self):
        return self.layout


class ColumnMapper(pn.viewable.Viewer):
    def __init__(
        self,
        data_fields,
        FileSelectorParams={},
        name="Selected File",
        default_file="",
        **params,
    ):
        super().__init__(**params)

        self.data_fields = data_fields

        # Create the FileSelectorModal widget
        self.input_file = FileSelectorModal(
            name=name,
            FileSelectorParams=FileSelectorParams,
            default_file=default_file,
        )

        # Create a dictionary to hold the Select widgets for mapping
        self.mapping_widgets = {}

        # self.input_file.close_modal_button.on_click(self.update_column_select)

        bound_function = pn.bind(
            self.update_column_select, self.input_file.selected_file
        )

        # Create the layout
        self.column_mapper = pn.Column()
        self.layout = pn.Column(self.input_file, self.column_mapper, bound_function)

    def update_column_select(self, event):
        self.create_mapping_widgets()

        file_path = self.input_file.selected_file.value
        if file_path and Path(file_path).is_file():
            file_path = Path(file_path)
            if file_path.exists():
                if file_path.suffix == ".csv":
                    columns = pd.read_csv(file_path, nrows=0).columns.tolist()
                elif file_path.suffix == ".shp":
                    self.gdf = gpd.read_file(file_path, rows=0)
                    columns = self.gdf.columns.tolist()
            columns.append(None)
            for column in self.mapping_widgets:
                self.mapping_widgets[column].options = {k: k for k in columns}
                self.mapping_widgets[column].value = None
                self.mapping_widgets[column].visible = True

    def create_mapping_widgets(self):
        self.mapping_widgets.clear()
        for column in self.data_fields:
            self.mapping_widgets[column] = pn.widgets.Select(
                name=column, options=[], visible=False
            )
        self.column_mapper.extend(self.mapping_widgets.values())

    def __panel__(self):
        return self.layout


class CommandRunner(Viewer):
    """
    Manages running a command in a subprocess and displaying the output
    in a Panel Terminal widget.  Prevents concurrent runs.
    """

    def __init__(self, **params):
        self.terminal = pn.widgets.Terminal(height=300)
        self.process = None  # Store the subprocess
        super().__init__(**params)

    def run_command(self, command):
        """
        Runs the given command in a subprocess, ensuring only one
        process runs at a time.
        """
        if self.process and self.process.poll() is None:
            self.terminal.write(
                "A command is already running. Please wait or kill it.\n"
            )
            return

        def process_output():
            self.terminal.clear()
            self.process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )

            for line in iter(self.process.stdout.readline, ""):
                self.terminal.write(line)

            self.process.stdout.close()
            self.process.wait()
            self.terminal.write("Command finished.\n")

        threading.Thread(target=process_output, daemon=True).start()

    def __panel__(self):
        return self.terminal


class FileFolderPicker(Viewer):
    def __init__(
        self,
        name=None,
        folders=[],
        file_pattern=None,
        only_folders=False,
        data_fields=[],
        **params,
    ):

        self.field_name = name
        self.data_fields = data_fields
        self.only_folders = only_folders

        partitions = [
            Path(p.mountpoint)
            for p in psutil.disk_partitions()
            if "/System/" not in p.mountpoint
        ]
        partitions.insert(0, Path.home())
        partitions = folders + partitions  # Add custom folders to the list

        if only_folders:
            self.file_pattern = ""
            # self.default_file = partitions[0]
            if self.field_name is None:
                self.field_name = "Folder"
        else:
            self.file_pattern = file_pattern or "*"
            # self.default_file = ""
            if self.field_name is None:
                name = f"File ({self.file_pattern})"

        self.drive_picker = pn.widgets.Select(
            name="Drive",
            options=partitions,
            value=partitions[0],
        )
        self.widgets = {}
        self.column_mapper = pn.Column()
        bound_function = pn.bind(self.update_root_folder, self.drive_picker)

        self.update_root_folder(None)
        self.layout = pn.Column(self.drive_picker, self.column_mapper, bound_function)

    def update_root_folder(self, event, default_file=""):
        self.widgets.clear()
        if self.only_folders:
            default_file = self.drive_picker.value
        else:
            default_file = ""

        if len(self.data_fields) > 0:
            self.widgets["picker"] = ColumnMapper(
                data_fields=self.data_fields,
                name=self.field_name,
                FileSelectorParams={
                    "directory": self.drive_picker.value,
                    "file_pattern": self.file_pattern,
                },
                default_file=str(default_file),
            )
        else:
            self.widgets["picker"] = FileSelectorModal(
                name=self.field_name,
                FileSelectorParams={
                    "directory": self.drive_picker.value,
                    "file_pattern": self.file_pattern,
                },
                default_file=str(default_file),
            )
        self.column_mapper.clear()
        self.column_mapper.extend(self.widgets.values())

    def get_selected(self):
        path = ""
        column_mappings = {}
        picker = self.widgets.get("picker", None)
        if type(picker) == FileSelectorModal:
            path = picker.selected_file.value

        if type(picker) == ColumnMapper:
            path = picker.input_file.selected_file.value
            for col in picker.data_fields:
                column_mappings[col] = picker.mapping_widgets[col].value
        return {"path": path, "column_mappings": column_mappings}

    def set_selected(self, path, column_mappings={}):
        picker = self.widgets.get("picker", None)

        if type(picker) == FileSelectorModal:
            picker.selected_file.value = path

        if type(picker) == ColumnMapper:
            picker.input_file.selected_file.value = path
            for k, v in column_mappings.items():
                picker.mapping_widgets[k].value = v

    def __panel__(self):
        return self.layout
