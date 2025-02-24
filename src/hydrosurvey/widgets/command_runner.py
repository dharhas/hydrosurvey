import subprocess
import threading

import geopandas as gpd
import pandas as pd
import panel as pn
from panel.viewable import Viewer

pn.extension("modal", "terminal")


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
