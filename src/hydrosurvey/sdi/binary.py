import itertools
import struct
import warnings
from datetime import date, datetime
from io import BytesIO

import numpy as np
import pandas as pd


def read(filepath, as_dataframe=False, separate=True, file_format="bin"):
    dataset = Dataset(filepath)

    if as_dataframe:
        d = dataset.as_dict(separate=False, file_format=file_format)
        df = (
            pd.DataFrame(
                {
                    key: d[key]
                    for key in d
                    if key
                    not in [
                        "date",
                        "filepath",
                        "file_version",
                        "survey_line_number",
                        "intensity",
                    ]
                }
            )
            .rename(columns={"trace_num": "trace"})
            .set_index("trace")
            .assign(survey_line_number=d["survey_line_number"])
            .assign(date=d["date"])
        )
        df["datetime"] = pd.to_datetime(
            df["date"].astype(str)
            + " "
            + df["hour"].astype(str)
            + ":"
            + df["minute"].astype(str)
            + ":"
            + (df["second"] + df["microsecond"] * 1e-6).astype(str)
        )
        return df

    return dataset.as_dict(separate=separate, file_format=file_format)


class Dataset(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.parsed = False

    def as_dict(self, separate=True, file_format="bin"):
        """Returns the SDI data as a dict. Data is collected and stored in the
        binary file as a sequence of traces, cycling between sampling
        frequencies. Each vertical column of intensity data is a trace and has
        various other readings stored along with it. If the `separate` keyword
        is True (default), then the data for each frequency will be split into
        distinct frequencies which will be a list of frequency dicts in the
        mapped to the 'frequencies' key. If `separate` is False, then data
        will be interleaved in the same way that it is collected and stored in
        the binary file format. The keys are as follows (note that not all
        fields will be available, depending on binary file version number):

        File-wide information:
            'date':
                The date that the survey file was collected. This is derived
                from the first digits of the filename, which is how the
                instruments record the date.
            'file_version':
                Version of the SDI binary file format.
            'filepath':
                The path to the SDI binary file.
            'survey_line_number':
                The line number that this file represents. This is derived from
                the filename.

        Trace-level information:
            'antenna_e1':
                Meters above the geoid. As from Hgt field of NMEA GGA log or
                calculated from HyPack. Only available in versions >= '4.2'
            'antenna_r1':
                Meters above the water line. Set by the user. Only available
                in versions >= '4.2'
            'blanking_pnt':
                Search for bottom must start after this data point.
            'clock':
                4 byte PC clock tick count since midnight. 1193180/65536 ticks
                per second.
            'cycles':
                Commanded In the output pulse train. Results may vary,
                depending on the hardware. Only available in versions >= '4.0'
            'data_offset':
                This is normally zero or one. Indicates sampling of the start
                of the output pulse was delayed by this many samples.
            'depth_pnt':
                Index of DepthRl in data array.
            'depth_r1':
                In meters below mean water level. In versions <= 4.1 was below
                geoid.
            'display_range':
                Maximum depth displayable, In meters. I.e. transducer range +
                Draft.
            'draft':
                Water line to transducer, in meters. Versions >= 4.2 should use
                Draft.
            'easting':
                Values of x in the coordinate reference system that the data
                was was configured for at the time of collection. Values are
                repeated until the instrumentation's attached GPS unit updates
                its coordinates. For an interpolated approximation of repeated
                values, see 'interpolated_easting'. Only available in
                versions >= '3.3'
            'event':
                This is as if EventLen is a ShortString with the extra chars
                truncated. The first event will have 'Recording ' plus the
                Filename field. Stores HyPack event numbers as well as user
                commemts.
            'event_len':
                Zero to a maximum of 31. If zero, the event field is not
                present.
            'gain':
                0..7 Only available in versions >= '4.0'
            'gps_mode':
                From HyPack or NMEA GGA, PRTKA or GLL logs. -1 if not
                received, timed out or field = ''. Only available in
                versions >= '4.3'
            'hdop':
                Horizontal Dilution Of Precision in meters. -1 if invalid.
                Only available in versions >= '4.3'
            'heave':
                If a heave sensor is available and calibrated with the
                instrumentation, this value represents amount of vertical lift
                the boat is experiencing during the moment the trace is
                recorded.
            'hour':
                Derived from the clock value.
            'intensity':
                Recorded intensity values
            'interpolated_easting':
                Values of x in the coordinate reference system that the data
                was was configured for at the time of collection. These values
                are an interpolated approximation of raw easting values
                that are repeated until the instrumentation's attached GPS unit
                updates its coordinates. For the raw, repeated values see
                'easting'.  Only available in versions >= '3.3'
            'interpolated_latitude':
                Latitude in the WGS84 coordinate reference system.  These
                values are an interpolated approximation of raw latitude values
                repeated until the instrumentation's attached GPS unit updates
                its coordinates. These are also . For the raw, repeated values
                see 'latitude'.  See also northing and interpolated_northing.
                Only available in versions >= '3.0'
            'interpolated_longitude':
                Longitude in the WGS84 coordinate reference system. These
                values are an interpolated approximation of raw longitude
                values that are repeated until the instrumentation's attached
                GPS unit updates its coordinates. For the raw, repeated values
                see 'longitude'. See also easting and interpolated_easting.
                Only available in versions >= '3.0'
            'interpolated_northing':
                Values of y in the coordinate reference system that the data
                was was configured for at the time of collection. These values
                are an interpolated approximation of raw northing values that
                are repeated until the instrumentation's attached GPS unit
                updates its coordinates. For the raw, repeated values see
                'northing'.  Only available in versions >= '3.3'
            'kHz':
                If separate == True, then this will be a single value.
                Otherwise, it will be an array.
            'latitude':
                Latitude in the WGS84 coordinate reference system. Values are
                repeated until the instrumentation's attached GPS unit updates
                its coordinates. See also northing and interpolated_northing.
                Only available in versions >= '3.0'
            'longitude':
                Longitude in the WGS84 coordinate reference system. Values are
                repeated until the instrumentation's attached GPS unit updates
                its coordinates. See also easting and interpolated_easting.
                Only available in versions >= '3.0'
            'max_window':
                Bottom of windowed depth the user viewed while recording data.
                In meters. See MinPntRl and NumPntRl.
            'microsecond':
                Derived from the clock value.
            'min_pnt_r1':
                Index into zero based data array of window top - can start, end
                at fraction.
            'min_window':
                Top of windowed depth the user viewed while recording data. In
                Meters. See MinPntRl.
            'minute':
                Derived from the clock value.
            'northing':
                Values of y in the coordinate reference system that the data
                was configured for at the time of collection. Values are
                repeated until the instrumentation's attached GPS unit updates
                its coordinates. For an interpolated approximation of repeated
                values, see 'interpolated_northing'. Only available in
                versions >= '3.3'
            'num_pnt_r1':
                Number of data points in window - can start, end at fraction
            'num_pnts':
                Number of 16 bit data points in the array. RangePnt + 2 m (1 m
                after ver 3.1?)
            'offset':
                DataPos = File position (after reading Offset) + Offset. After
                reading the Record Header, seek to the DataPos for forward
                compatibility with later versions. Only available in
                versions >= '3.1'.
            'options':
                1=Bipolar: ver <= 1.6 = 0, 2= Latitude has Y, Longitude has X:
                ver < 3.3, 4=Rtk mode. Only available in versions >= '3.1'.
            'previous_offset':
                The size of the previous record in bytes. Not currently
                utilized. Only available in versions >= '4.0'
            'pixel_resolution':
                Derived vertical resolution of a single pixel, in meters. Based
                on rate and speed of sound.
            'power':
                0..3 or 0..7 Only available in versions >= '4.0'
            'range_pnt':
                Search for bottom will not go past this point.
            'rate':
                A/D samples per second. In versions <= 1.6 this field was not
                present, set to 25000.
            'second':
                Derived from the clock value.
            'spdos':
                Speed of sound, in meters per second.
            'spdos_units':
                Original units that speed of sound was set with before
                converting to meters. 0 = feet, 1 = meters.
            'tide':
                Mean water line - geoid, in meters. Versions >= 4.2 should use
                Tide.
            'trace_num':
                Sequential record number within this file, starting at 1.
            'transducer':
                1..5 in order of frequency (bottom to sub-bottom). For example:
                1 = 200kHz, 5 = 3.5kHz. Only available in versions >= '3.1'.
                If an earlier version is being read, Transducer should be
                inferred from kHz.
            'units':
                Field that represents the units that the data originally was
                recorded in: 0 = feet, 1 = meters, 2 = fathoms. Note that
                values have been normalized SI units as described.
            'volts':
                Max volts 0=10, 1=5, 2=2.5, 3=1.25 volts. Min depends on
                Bipolar bit in Options. Only available in versions >= '4.0'
        """
        if not self.parsed:
            self.parse(file_format=file_format)

        d = {
            "date": self.date,
            "filepath": self.filepath,
            "file_version": self.version,
            "survey_line_number": self.survey_line_number,
        }

        if file_format == "bss":
            d.update(
                {
                    "start_datetime": self.start_datetime,
                    "end_datetime": self.end_datetime,
                    "depth_r1": self.trace_metadata.pop("depth_r1")
                    + self.trace_metadata["draft"],
                }
            )

        if separate:
            d["frequencies"] = self.frequencies
        else:
            d["intensity"] = self.intensity_image
            for key, array in self.trace_metadata.items():
                d[key] = array
        return d

    def assemble_frequencies(self):
        """build clean dicts containing frequency metadata and intensity images
        for all available frequencies
        """
        frequencies = []

        transducers = np.unique(self.trace_metadata["transducer"])
        for transducer in transducers:
            freq_dict = {}
            freq_mask = np.where(self.trace_metadata["transducer"] == transducer)

            unique_kHzs = np.unique(self.trace_metadata["kHz"][freq_mask])
            if len(unique_kHzs) > 1:
                raise RuntimeError(
                    "The file has been corrupted or there is a bug in this "
                    "parsing library. Either way, we can't figure out what "
                    "data to return."
                )
            else:
                khz = unique_kHzs[0]

            for key, array in self.trace_metadata.items():
                freq_dict[key] = array[freq_mask]

            freq_dict["intensity"] = self.intensity_image[freq_mask]
            freq_dict["kHz"] = khz
            frequencies.append(freq_dict)

        return sorted(frequencies, key=lambda d: d["kHz"])

    def convert_to_meters_array(self, units):
        """Given an array of unit integers, returns an array of conversion
        factors suitable for converting another array to meters. This is used
        for converting trace data that depends on the units field.
        """
        # Based on this excerpt from the spec:
        #   6   1 Units          Byte                 0 = feet, 1 = meters, 2 = fathoms.  Fields
        # that use Units are noted
        #   7   1 Spdosunits     Byte                 0 = feet, 1 = meters. Used by Spdos only

        units_factors = {
            0: 0.3048,  # feet to meters
            1: 1.0,  # meters to meters
            2: 1.8288,  # fathoms to meters
        }
        convert_to_meters = np.zeros(len(units), dtype=float)

        for unit_value, conversion_factor in units_factors.items():
            convert_to_meters[units == unit_value] = conversion_factor

        is_zero = convert_to_meters == 0
        if np.any(is_zero):
            if len(convert_to_meters[is_zero]) < 5:
                convert_to_meters[is_zero] = convert_to_meters[~is_zero][0]
                warnings.warn(
                    "Encountered a few (< 5) unsupported units in units array, replacing with units from first valid field in array"
                )
            else:
                raise NotImplementedError("Encountered unsupported units.")

        return convert_to_meters

    def filter_x_and_y(self, original_x, original_y):
        """Given an array of raw x and y values return a version
        where impossibly noisey values (GPS glitches) have been removed.
        """
        _, x_dedup_idx = _deduplicate(original_x)
        _, y_dedup_idx = _deduplicate(original_y)

        dedup_idx = np.unique(np.hstack([x_dedup_idx, y_dedup_idx]))
        x = original_x.copy()[dedup_idx]
        y = original_y.copy()[dedup_idx]

        if (x.max() - x.min()) <= 200:
            x_std_factor = 7
        else:
            x_std_factor = 5

        if (y.max() - y.min()) <= 200:
            y_std_factor = 7
        else:
            y_std_factor = 5
        x_out = np.abs(x - np.median(x)) > x_std_factor * x.std()
        y_out = np.abs(y - np.median(y)) > y_std_factor * y.std()

        out_mask = x_out + y_out

        good_x = original_x.copy()
        good_y = original_y.copy()

        if np.any(out_mask):
            nan_mask = (good_x == x[out_mask]) + (good_y == y[out_mask])
            good_x[nan_mask] = np.nan
            good_y[nan_mask] = np.nan

            good_x = _fill_nans_with_last(good_x)
            good_y = _fill_nans_with_last(good_y)

            # call this recursively, because outliers can be so extreme that
            # multiple passes are necessary
            good_x, good_y = self.filter_x_and_y(good_x, good_y)

        return good_x, good_y

    def parse(self, file_format="bin"):
        """Parse the entire file and initialize attributes"""
        with open(self.filepath, "rb") as f:
            data = f.read()

        fid = BytesIO(data)
        data_length = len(data)

        if file_format == "bin":
            header = self.parse_file_header(fid)
            self.version = header["version"]
            self.survey_line_number = header["filename"]
            # header = self.parse_file_header(fid)
            self.resolution_cm = header["resolution_cm"]
            self.date = datetime.strptime(self.survey_line_number[:6], "%y%m%d").date()
            self.parse_records(fid, data_length)
        elif file_format == "bss":
            header = self.parse_bss_file_header(fid)
            self.file_header = header
            self.version = header["version"]
            self.survey_line_number = header["filename"]
            self.date = datetime.strptime(self.survey_line_number[:6], "%y%m%d").date()
            self.parse_bss_records()

        self.frequencies = self.assemble_frequencies()
        self.parsed = True

    def parse_file_header(self, f):
        """
        Reads in file header information. Based on the specification:
            Offset Size          File Header

            0   8 Filename       array[1..8] of Char  Original printable base filename.  All 8 chars
                                                      are used.  Formed using date and file number
                                                      with YYMMDDFF where FF = '01'..'99','9A'..'ZZ'
            8   1 Cr             Char constant 13H
            9   1 Lf             Char constant 10H
           10   1 Version        Byte                 1st nibble = major, 2nd = minor
                                                      43H = version 4.3
           11   1 ResCm          Byte                 Sample resolution in centimeters.  Used in
                                                      versions before 1.6, now zero. Superseeded
                                                      by the Rate field
        """
        f.seek(0)

        filename, cr, lf, version_byte, resolution_cm = struct.unpack(
            "<8s2cBB", f.read(12)
        )
        major_version = version_byte >> 4
        minor_version = version_byte & 0xF

        version = "%s.%s" % (major_version, minor_version)
        if version <= "3.2":
            raise NotImplementedError(
                "Reading of file formats <= 3.2 Not Supported, File Version="
                + str(version)
            )

        return {
            "filename": filename.decode("latin-1"),
            "version": version,
            "resolution_cm": resolution_cm,
        }

    def parse_bss_file_header(self, f):
        """
        Reads in file header information. Based on the specification:
            Offset Size          File Header

         66      64   Filename           TBssString  Original filename if possible, no path
        130       2   FileNumber         U16     1 is first file of the day
        132       2   FileVersion,       TVer    This TBssHeader, TBssRec version - 1000 = 1.0.0
        """

        f.seek(66)

        filename = struct.unpack("<64s", f.read(64))[0].decode("utf16")
        file_version = struct.unpack("<H", f.read(2))[0]
        file_number = struct.unpack("<H", f.read(2))[0]

        f.seek(146)
        self.spdos = struct.unpack("<d", f.read(8))[0]

        f.seek(158)
        self.start_datetime = struct.unpack("<d", f.read(8))[0]
        f.seek(360)
        self.end_datetime = struct.unpack("<d", f.read(8))[0]
        f.seek(170)
        self.units = struct.unpack("<B", f.read(1))[0]

        return {
            "filename": filename,
            "version": file_version,
            "file_number": file_number,
            "date": date.today(),
        }

    def parse_records(self, fid, data_length):
        pre_structs = [
            ("offset", "H", np.uint16),
            ("trace_num", "l", np.int32),
            ("units", "B", np.uint8),
            ("spdos_units", "B", np.uint8),
            ("spdos", "h", np.int16),
            ("min_window10", "h", np.int16),
            ("max_window10", "h", np.int16),
            ("draft100", "h", np.int16),
            ("tide100", "h", np.int16),
            ("heave_cm", "h", np.int16),
            ("display_range", "h", np.int16),
            ("depth_r1", "f", np.float32),
            ("min_pnt_r1", "f", np.float32),
            ("num_pnt_r1", "f", np.float32),
            ("blanking_pnt", "h", np.int16),
            ("depth_pnt", "h", np.int16),
            ("range_pnt", "h", np.int16),
            ("num_pnts", "h", np.int16),
            ("clock", "l", np.int32),
            ("hour", "B", np.uint8),
            ("minute", "B", np.uint8),
            ("second", "B", np.uint8),
            ("centisecond", "B", np.uint8),
            ("rate", "l", np.int32),
            ("kHz", "f", np.float32),
            ("event_len", "B", np.uint8),
        ]
        event_struct = [("event", None, None)]
        post_structs = [
            ("longitude", "d", np.float64),
            ("latitude", "d", np.float64),
            ("transducer", "B", np.uint8),
            ("options", "B", np.uint8),
            ("data_offset", "B", np.uint8),
        ]
        if self.version >= "3.3":
            post_structs.append(("easting", "d", np.float64))
            post_structs.append(("northing", "d", np.float64))
        if self.version >= "4.0":
            post_structs.append(("cycles", "B", np.uint8))
            post_structs.append(("volts", "B", np.uint8))
            post_structs.append(("power", "B", np.uint8))
            post_structs.append(("gain", "B", np.uint8))
            post_structs.append(("previous_offset", "H", np.int32))
        if self.version >= "4.2":
            post_structs.append(("antenna_e1", "f", np.float32))
            post_structs.append(("antenna_ht", "f", np.float32))
            post_structs.append(("draft", "f", np.float32))
            post_structs.append(("tide", "f", np.float32))
        if self.version >= "4.3":
            post_structs.append(("gps_mode", "b", np.int16))
            post_structs.append(("hdop", "f", np.float32))

        all_structs = pre_structs + event_struct + post_structs

        # intitialize dict of trace elements
        raw_trace = dict([[name, []] for name, fmt, dtype in all_structs])

        trace_intensities = []

        # pre-compute format, names and size for unpacking
        pre_fmt, pre_names, pre_size = self._split_struct_list(pre_structs)
        post_fmt, post_names, post_size = self._split_struct_list(post_structs)

        npos = 12
        fid.seek(npos)

        # loop through data extract traces. the length of the event string
        # changes between traces and is defined just before it (event_len), so
        # parsing a line is split into three stages: pre-event, event, and
        # post-event
        while npos < data_length:
            pre_record = struct.unpack(pre_fmt, fid.read(pre_size))
            pre_dict = dict(list(zip(pre_names, pre_record)))

            size = pre_dict["event_len"]
            if size > 0:
                event = struct.unpack("<" + str(size) + "s", fid.read(size))[0]
            else:
                event = ""
            raw_trace["event"].append(event)

            post_record = struct.unpack(post_fmt, fid.read(post_size))
            post_dict = dict(list(zip(post_names, post_record)))

            for key, value in itertools.chain(
                iter(pre_dict.items()), iter(post_dict.items())
            ):
                raw_trace[key].append(value)

            fid.seek(npos + pre_dict["offset"] + 2)

            size = pre_dict["num_pnts"]
            intensity = struct.unpack("<" + str(size) + "H", fid.read(size * 2))
            trace_intensities.append(intensity)
            npos = int(fid.tell())

        self.raw_trace = raw_trace
        self.intensities = trace_intensities
        self.trace_metadata = self.process_raw_trace(raw_trace, all_structs)
        self.intensity_image = self._normalize_scale(_fill_nans(trace_intensities))

    def parse_bss_records(self):
        with open(self.filepath, "rb") as f:
            data = f.read()

        fid = BytesIO(data)
        data_length = len(data)
        self.version = 1000

        rec_structs = [
            ("bss_size", "H", np.uint32),
            ("prev_record_size", "L", np.uint32),
            ("num_pnts", "L", np.uint32),
            ("time_tag", "d", np.float32),
            ("trace_num", "L", np.uint32),
            ("rate", "L", np.uint32),
            ("transducer", "B", np.uint8),
            ("bipolar", "?", np.bool_),
            ("sats", "b", np.int8),
            ("hpr_status", "B", np.uint8),
            ("heave", "f", np.float32),
            ("pitch", "f", np.float32),
            ("roll", "f", np.float32),
            ("heading", "f", np.float32),
            ("course", "f", np.float32),
            ("kHz", "f", np.float32),
            ("draft", "f", np.float32),
            ("tide", "f", np.float32),
            ("antenna_el", "f", np.float32),
            ("blanking", "f", np.float32),
            ("window_min", "f", np.float32),
            ("window_max", "f", np.float32),
            ("xd_range", "f", np.float32),
            ("depth_r1", "f", np.float32),
            ("depth_r2", "f", np.float32),
            ("depth_r3", "f", np.float32),
            ("depth_r4", "f", np.float32),
            ("depth_r5", "f", np.float32),
            ("volts", "f", np.float32),
            ("longitude", "d", np.float32),
            ("latitude", "d", np.float32),
            ("x", "d", np.float32),
            ("y", "d", np.float32),
            ("hdop", "f", np.float32),
            ("cycles", "b", np.int8),
            ("power", "b", np.int8),
            ("gain", "b", np.int8),
            ("gps_mode", "b", np.int8),
            ("comment", "64s", np.string_),
            ("select", "B", np.uint8),
            ("channel", "B", np.uint8),
        ]

        # intitialize dict of trace elements
        raw_trace = dict([[name, []] for name, fmt, dtype in rec_structs])

        trace_intensities = []

        fmt, names, size = self._split_struct_list(rec_structs)
        npos = 372
        fid.seek(npos)
        while npos < data_length:
            record = struct.unpack(fmt, fid.read(size))
            record_dict = dict(list(zip(names, record)))
            for key, value in record_dict.items():
                raw_trace[key].append(value)

            fid.seek(int(fid.tell()) + 6)

            data_size = record_dict["num_pnts"]
            intensity = struct.unpack(
                "<" + str(data_size) + "h", fid.read(data_size * 2)
            )
            trace_intensities.append(intensity)
            npos = int(fid.tell())
            self.raw_trace = raw_trace
            self.intensity = intensity

        self.trace_metadata = self.process_raw_trace(
            raw_trace, rec_structs, file_format="bss"
        )
        self.intensities = trace_intensities
        self.raw_trace = raw_trace
        self.intensity_image = self._normalize_scale(_fill_nans(trace_intensities))

    def process_raw_trace(self, raw_trace, all_structs, file_format="bin"):
        """Clean up raw trace data - convert lists to appropriately typed
        np.arrays of uniform units (meters for distance values)
        """
        processed = {}
        # convert raw trace lists to arrays
        for key, value, dtype in all_structs:
            array = np.array(raw_trace[key], dtype=dtype)
            processed[key] = array

        # convert unit-dependent fields to meters - first by converting them to
        # whole units (feet, meters, fathoms), then applying conversion factor
        # some keys are depreciated and overwritten in recent versions of format
        # 'draft100' and 'tide100' for example are ignored it draft and tide are
        # present
        units = processed.get("units", 0)
        if np.any(units > 2):
            raise NotImplementedError(
                "This sdi file contains unsupported units.",
            )

        if file_format == "bin":
            convert_to_meters = self.convert_to_meters_array(units)
            keys_to_convert = [
                "min_window",
                "max_window",
                "display_range",
            ]

            for raw_key in ["min_window10", "max_window10"]:
                array = processed.pop(raw_key)
                new_key = raw_key[:-2]
                processed[new_key] = array / 10.0

            for raw_key in ["draft100", "tide100"]:
                array = processed.pop(raw_key)
                new_key = raw_key[:-3]
                if new_key not in list(raw_trace.keys()):
                    keys_to_convert.append(new_key)
                    processed[new_key] = array / 100.0

            for key in keys_to_convert:
                processed[key] = processed[key] * convert_to_meters

            # convert heave to meters
            heave_cm = processed.pop("heave_cm")
            processed["heave"] = heave_cm * 100.0

            # convert speed of sound to meters
            convert_spdos = self.convert_to_meters_array(processed["spdos_units"])
            processed["spdos"] = processed["spdos"] * convert_spdos

            # replace centiseconds with microseconds
            processed["microsecond"] = (
                processed["centisecond"].astype(np.uint32) * 10000
            )
            processed.pop("centisecond")

            x_col = "easting"
            y_col = "northing"
        else:
            processed["spdos"] = np.ones_like(processed["longitude"]) * self.spdos
            x_col = "x"
            y_col = "y"
        # calculate pixel resolution
        processed["pixel_resolution"] = (processed["spdos"] * 1.0) / (
            2 * processed["rate"]
        )

        for x_key, y_key in [("longitude", "latitude"), (x_col, y_col)]:
            if x_key in processed and y_key in processed:
                # filter out bad values
                x, y = self.filter_x_and_y(processed[x_key], processed[y_key])
                if x_key == "x":
                    x_key = "easting"
                if y_key == "y":
                    y_key = "northing"

                processed[x_key] = x
                processed[y_key] = y

                # interpolate values
                processed["interpolated_" + x_key] = _interpolate_repeats(x)
                processed["interpolated_" + y_key] = _interpolate_repeats(y)

        return processed

    def _normalize_scale(self, intensity_image):
        """
        Normalize and rescale trace intensities to [0, 1]

        Per Spec: Check bit zero of Options to see if the data is bipolar.
        If it is not set, the data is unipolar in unsigned words 0..65535
        If bit zero is set, some conversion is needed. Flip the high bit
        (bit 15) of each word to get signed bipolar smallints -32768..32767

        Pascal code does not seem in step with spec. see below.

        Pascal Conversion Code:
            if(header.Version > $16) then
            begin
                MinValue := 32768;
                for point := StartSample to EndSample do
                begin
                  if((not UNIPOL) or (header.Version >= 80)) then
                  begin
                    RealValue := abs(integer(RawPnts[point]) - 32768)/128;
                  end
                  else begin
                    RealValue := RawPnts[point]/257.0;
                  end;
                  DataValue := byte(round(RealValue));
                  NumData := NumData + 1;
                  TraceDataP^[NumData] := DataValue;
                  if(DataValue < MinValue) then MinValue := DataValue;
                end;
            end;
        """
        if self.version >= "5.0" or self.version == 1000:
            return np.abs(intensity_image + np.float64(32768)) / np.float64(65535)
        else:
            index_200khz = self.raw_trace["transducer"] == 1
            scaled_image = np.zeros_like(intensity_image)
            scaled_image[index_200khz, :] = intensity_image[
                index_200khz, :
            ] / np.float64(65535)
            scaled_image[~index_200khz, :] = np.abs(
                intensity_image[~index_200khz, :] - np.float64(32768)
            ) / np.float64(32768)
            return scaled_image

    def _split_struct_list(self, struct_list):
        """Helper method for splitting struct lists into components for
        processing files. Returns a tuple containing (fmt, names, size) where
        fmt is a single struct string suitable for use with struct.unpack(),
        names is the list of names to associate with each element of a
        corresponding unpacked tuple and size is the size (in bytes) of the
        string of data that should be unpacked.
        """
        fmt = "<" + "".join([fmt for name, fmt, dtype in struct_list])
        names = [name for name, _, _ in struct_list]
        size = struct.calcsize(fmt)

        return fmt, names, size


def _deduplicate(arr):
    """given an array, returns a tuple containing values that are not repeated
    and the indexes to those values from the original array
    """
    tmp = arr.copy()
    tmp[1:] = arr[1:] - arr[:-1]
    arr_index = np.nonzero(tmp)[0]
    arr_values = arr[arr_index]

    return arr_values, arr_index


def _fill_nans(lists):
    """take list of variable-length lists of floats and convert to a np.array
    of shape (len(lists), max_length), padding any row that is less than
    max_length with NaNs
    """
    # trace intensity are variable length if power changes mid-trace, so we
    # need to build a clean np-array image, filling with nans
    lengths = np.array([len(i) for i in lists], dtype=np.float64)

    # find discontinuities
    (discontinuities,) = np.nonzero(lengths[1:] - lengths[:-1])

    # convert to a list of indexes into lists where
    # discontinuities exist - add 1 to discontinuities to count for
    # shortening lengths during the index trick to find the
    # discontinuities
    adjusted = (discontinuities + 1).tolist()

    # adjust discontinuity to use as for splitting the lists
    # lists
    starts = [0] + adjusted
    ends = adjusted + [len(lists)]

    def _padded_sub_array(lists, start, end, to_length):
        sub_array = np.array(lists[start:end])
        fill_nans = np.nan + np.zeros(
            (sub_array.shape[0], to_length - sub_array.shape[1])
        )
        return np.column_stack([sub_array, fill_nans])

    max_length = np.max(lengths)
    array = np.vstack(
        [
            _padded_sub_array(lists, start, end, int(max_length))
            for start, end in zip(starts, ends)
        ]
    )

    return array


def _interpolate_repeats(arr):
    """Returns an array where repeated sequential values are linearly
    interpolated to the next non-repeated value. For the final values, assume
    that linear relationship of the previous pair of points applies.  This is
    used to interpolate gps track values that are repeated until the next
    update.

    Example::

        arr = np.array([1.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
        _interpolate_repeats(arr) == np.array([ 1.0, 1.33333333, 1.66666667, 2.,  2.5, 3.0, 3.5])
    """
    filled = _fill_nans_with_last(arr)
    filled_values, filled_index = _deduplicate(filled)

    # add one more point so final repeated values are interpolated assuming the
    # same relationship as the last pair of values
    if len(filled_index) > 1:
        filled_index = np.append(
            filled_index, (2 * filled_index[-1]) - filled_index[-2]
        )
        filled_values = np.append(
            filled_values, (2 * filled_values[-1]) - filled_values[-2]
        )
    else:
        filled_index = np.append(filled_index, (2 * filled_index[-1]))
        filled_values = np.append(filled_values, (2 * filled_values[-1]))

    return np.interp(np.arange(len(filled)), filled_index, filled_values)


def _fill_nans_with_last(arr):
    """Returns an array where nan values are filled to whatever the previous
    non-NaN value was. If the array starts with NaN values, then those will be
    set to the first non-NaN value.
    """
    tmp = arr.copy()

    # if the array starts with a NaN, then replace it with the first non-NaN
    mask = np.isnan(tmp)
    if len(tmp) == 0 or np.all(mask):
        raise ValueError("Array must contain some non-NaN values.")
    if mask[0]:
        tmp[0] = tmp[~mask][0]

    # there's probably a more efficient way to do this; this loops as many
    # times as the longest string of NaNs
    while True:
        mask = np.isnan(tmp)
        if not np.any(mask):
            break
        nan_index = np.where(mask)[0]
        tmp[nan_index] = tmp[nan_index - 1]

    return tmp
