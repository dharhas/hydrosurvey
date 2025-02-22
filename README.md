# HydroSurvey Tools

This is a groundup rewrite using modern pydata tools of algorithms originally described in my 2011 SciPy Talk - [Improving efficiency and repeatability of lake volume estimates using Python](https://proceedings.scipy.org/articles/Majora-ebaa42b7-013)


## Installation

1. Download this code with git or download a zip file (click the green code icon) and unzip
2. Download and install pixi from https://prefix.dev/
3. Open a cmd/terminal window and navigate to the folder that contains this software
4. run `pixi install` to install the software

## Usage

1. Open a cmd/terminal window in the folder with the code
2. run `pixi shell` in the terminal to activate the environment
3. now you will have a tool called hstools, if you type `hstools` you will get a help message.
4. `hstools new-config <configfilename>` will help you created a new config file with a guided wizard
5. `hstools interpolate-lake <configfilename>` will run the interpolation
6. `hstools gui` launches a gui version of the tool