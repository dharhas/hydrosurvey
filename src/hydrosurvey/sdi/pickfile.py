import numpy as np
import pandas as pd


def read(filename, as_dataframe=False):
    """
    Reads in a DepthPic pick file and returns dict that contains the surface number,
    the speed of sound (m/s), draft, tide and a numpy array of depths in meters
    ordered by trace number.

    To convert depths into pixel space use the following equation
    pixels_from_top_of_image = (depths - draft + tide)/pixel_resolution

    Note: We ignore position data and trace number fields as they are superfluous

    Format Example:
        Depth                                   <--- Always Depth (Possibly elevation in some setups, we don't have)
        2                                       <--- Surface Number (1=current, >2=preimpoundment)
        FEET                                    <--- Units of Depth
        1.48498560000000E+0003                  <--- Speed of Sound (m/s)
        4.57200000000000E-0001                  <--- Draft (m)
        0.00000000000000E+0000                  <--- Tide (m)
        TRUE                                    <--- Not sure what this is?
        2                                       <--- 1/2/3/4 (1=northing/easting,2=lat/lon,3=0/distance,4=northin/easting)
        -97.90635230   28.06836280     4.33 1   <--- X Y Depth TraceNumber
        ...

    """

    data = {}

    units_factors = {
        "feet": 0.3048,  # feet to meters
        "meters": 1.0,  # meters to meters
        "fathoms": 1.8288,  # fathoms to meters
    }

    with open(filename) as f:
        f.readline()
        data["surface_number"] = int(f.readline().strip("r\n"))
        units = f.readline().strip("\r\n").lower()
        convert_to_meters = units_factors[units]
        # speed of sound, draft and tide are always in m/s
        data["speed_of_sound"] = float(f.readline().strip("\r\n"))
        data["draft"] = float(f.readline().strip("\r\n"))
        data["tide"] = float(f.readline().strip("\r\n"))
        data["flag"] = f.readline().strip("\r\n")
        position_type = f.readline().strip("\r\n")
        if position_type == "3":
            cols = [1, 2]
        else:
            cols = [2, 3]

        depth, trace_number = np.genfromtxt(f, usecols=cols, unpack=True)
        data["trace_number"] = trace_number.astype(np.int32)
        data["depth"] = depth.astype(np.float32) * convert_to_meters

    if as_dataframe:
        return pd.DataFrame(
            {
                f"depth_surface_{data['surface_number']}": data["depth"],
                "trace": data["trace_number"],
            }
        ).set_index("trace")

    return data
