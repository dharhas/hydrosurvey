# HydroSurvey Tools

This is a groundup rewrite using modern pydata tools of algorithms originally described in my 2011 SciPy Talk - [Improving efficiency and repeatability of lake volume estimates using Python](https://proceedings.scipy.org/articles/Majora-ebaa42b7-013).

## Installation

1. Download this code with git or download a zip file (click the green code icon) and unzip
2. Download and install pixi from https://prefix.dev/
3. Open a cmd/terminal window and navigate to the folder that contains this software
4. run `pixi install` to install the software

## Usage

1. Open a cmd/terminal window in the folder with the code
2. run `pixi shell` in the terminal to activate the environment
3. now you will have a tool called hstools, if you type `hstools` you will get a help message.
4. `hstools new-config <config.toml>` will help you created a new config file with a guided wizard
5. `hstools interpolate-lake <config.toml>` will run the interpolation
6. `hstools compute-eac <dem.tif> <output.csv>` will create an elevation area capacity table from a dem
7. `hstools gui` launches a gui version of the tool

## Anisotropic Elliptical Inverse Distance Weighting (AEIDW) Lake Interpolation Algorithm

### Input files and parameters required

- CSV file with survey data, fields: x-coord, y-coord, current surface elevation, preimpoundment elevation (optional)
  - elevation: lake elevation at the boundary
  - max segment length: this is used to add more vertices to the centerline to improve interpolation accuracy
- Shapefile of Lake boundary at a particular elevation. Elevation value set in the attribute table
- Interpolation Centerline Shapefile: This defines the direction of interpolation in a particular polygon
  - polygon id: foreign key used to math centerlines with polygons
  - max segment lenght: this is used to add more vertices to the centerline to improve interpolation accuracy
- Interpolation Polygons Shapefile, in the attribute table the following values are set for each polygon
  - polygon id: foreign key used to connect polygons to centerlines
  - grid spacing: density of generated target points in each polygon that the survey data is interpolated to
  - priority: priority of the polygon, when polygons overlap target points in the overlap region use survey points from the higher priority polygon
  - interpolation method: type of interpolation used in the polygon (currently AEIDW or CONSTANT)
  - interpolation params: parameters needed by interpolation methos (currently ellipsivity for AEIDW or elevation value for CONSTANT)
  - Polygon Buffer: Use some survey data in the buffer region around the polygon to avoid interpolation artifacts near the polygon boundaries
  - nearest nieghbors: how many neighbors to include in the interpolation to each target point

### Algorithm

The essential idea of AEIDW algorithm is that along channel bathymetric depths are likely to be more similar to each other than across channel. So we transform the data into a coordinate system that follows the channel and then scale the across channel coordinate by an ellipsivity factor. After this we do a regular inverse distance wieghting. Since the across channel points are now further away, this causes the interpolation to weight along channel survey data higher than across channel survey data.

1. Add boundary data to survey data
2. iterate through polygons
3. Generate target points in each polygon
4. Convert survey data and target points in each polygon into "S-N" coordinates, where S=distance along centerline and N-perpendicular distance from centerline
5. Multiply "N" coordinate by "ellipsivity" factor.
6. Interpolate data using Inverse Distance Weighting algorithm
7. merge the target points with the original survey data
